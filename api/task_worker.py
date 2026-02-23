import asyncio
import logging
import os

from utils import get_file_manager

from .ffmpeg_executor import FFmpegExecutor
from .models import Task, TaskStatus
from .task_queue import TaskEvent, task_queue

logger = logging.getLogger(__name__)


class TaskWorker:
    """Worker that processes tasks from the queue."""

    _task_handlers = {}

    def get_file_manager(self):
        return get_file_manager()

    def __init__(self, worker_id: int):
        if "__MERGE_AUDIO_VIDEO__" not in self._task_handlers:
            # Register the unbound method, not the bound one
            self.register_task_handler("__MERGE_AUDIO_VIDEO__")(TaskWorker.handle_merge_audio_video)
        self.worker_id = worker_id
        self.s3_url = os.getenv("S3_ENDPOINT_URL", None)
        self.running = False

    @classmethod
    def register_task_handler(cls, command_name):
        def decorator(func):
            cls._task_handlers[command_name] = func
            return func

        return decorator

    async def process_task(self, task: Task) -> None:
        logger.info(f"Worker {self.worker_id}: Processing task {task.task_id}")
        task.status = TaskStatus.RUNNING
        await task_queue.publish(TaskEvent.TASK_STARTED, task)
        try:
            handler = self._task_handlers.get(task.command)
            if handler:
                await handler(self, task)
            else:
                await self.handle_default_ffmpeg_task(task)
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            logger.error(f"Worker {self.worker_id}: Task {task.task_id} error: {str(e)}")
            await task_queue.publish(TaskEvent.TASK_FAILED, task)

    async def handle_merge_audio_video(self, task: Task) -> None:
        file_manager = self.get_file_manager()
        video_url = task.input_files.get("video")
        if not video_url:
            raise Exception("Missing video input for merge-audio-video task")
        video_local = await file_manager.download_file(video_url, "loop_video.mp4")
        audio_files = []
        i = 0
        while True:
            key = f"audio_{i}"
            url = task.input_files.get(key)
            if not url:
                break
            fname = f"track_{i:03d}.mp3"
            audio_files.append(await file_manager.download_file(url, fname))
            i += 1
        if not audio_files:
            raise Exception("No audio files provided for merge-audio-video task")
        concat_list_path = os.path.join(file_manager.temp_dir, "concat.txt")
        with open(concat_list_path, "w") as f:
            for af in audio_files:
                f.write(f"file '{os.path.abspath(af)}'\n")
        merged_audio = os.path.join(file_manager.temp_dir, "merged_audio.mp3")
        concat_cmd = f"ffmpeg -y -f concat -safe 0 -i {concat_list_path} -c copy {merged_audio}"
        proc = await asyncio.create_subprocess_shell(
            concat_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        probe_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {merged_audio}"
        proc = await asyncio.create_subprocess_shell(
            probe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, _ = await proc.communicate()
        duration = float(out.decode().strip())
        output_filename = next(iter(task.output_files.values()), "output.mp4")
        output_path = file_manager.get_temp_file_path(output_filename)
        merge_cmd = (
            f"ffmpeg -y -stream_loop -1 -i {video_local} -i {merged_audio} "
            f"-map 0:v -map 1:a -shortest -c:v libx264 -preset fast -crf 18 "
            f"-c:a aac -b:a 192k -t {duration} {output_path}"
        )
        proc = await asyncio.create_subprocess_shell(
            merge_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        if proc.returncode != 0 or not os.path.exists(output_path):
            error_detail = err.decode() if err else out.decode()
            file_manager.cleanup()
            raise Exception(f"FFmpeg failed to create output file: {error_detail}")
        s3_key = f"youtube-merge/{task.task_id}/{output_filename}"
        url = file_manager.upload_to_s3(output_path, s3_key)
        task.output_urls = {"video": url}
        task.status = TaskStatus.COMPLETED
        logger.info(
            f"Worker {self.worker_id}: merge-audio-video task {task.task_id} completed successfully"
        )
        await task_queue.publish(TaskEvent.TASK_COMPLETED, task)
        file_manager.cleanup()

    async def handle_default_ffmpeg_task(self, task: Task) -> None:
        file_manager = self.get_file_manager()
        logger.info(f"Worker {self.worker_id}: Downloading files for {task.task_id}")
        local_files = await file_manager.download_files(task.input_files)
        output_local_paths: dict[str, str] = {}
        for out_key, out_name in task.output_files.items():
            output_local_paths[out_key] = file_manager.get_temp_file_path(out_name)
        logger.info(f"Worker {self.worker_id}: Executing FFmpeg for {task.task_id}")
        success, error_msg = await FFmpegExecutor.execute(
            command_args=task.command,
            input_files=local_files,
            output_files=output_local_paths,
        )
        if not success:
            task.status = TaskStatus.FAILED
            task.error_message = error_msg
            logger.error(f"Worker {self.worker_id}: Task {task.task_id} failed: {error_msg}")
            await task_queue.publish(TaskEvent.TASK_FAILED, task)
            file_manager.cleanup()
            return
        logger.info(f"Worker {self.worker_id}: Uploading output for {task.task_id}")
        task.output_urls = {}
        for out_key, local_path in output_local_paths.items():
            filename = task.output_files.get(out_key, out_key)
            s3_key = f"ffmpeg-outputs/{task.task_id}/{filename}"
            url = file_manager.upload_to_s3(local_path, s3_key)
            task.output_urls[out_key] = url
        task.status = TaskStatus.COMPLETED
        logger.info(f"Worker {self.worker_id}: Task {task.task_id} completed successfully")
        await task_queue.publish(TaskEvent.TASK_COMPLETED, task)
        file_manager.cleanup()

    async def start(self) -> None:
        """Start the worker to process tasks from the queue."""
        self.running = True
        logger.info(f"Worker {self.worker_id} started")

        try:
            while self.running:
                try:
                    # Get task from queue with timeout to allow graceful shutdown
                    task = await asyncio.wait_for(task_queue.dequeue(), timeout=1.0)
                    await self.process_task(task)
                except TimeoutError:
                    # No task available, continue waiting
                    continue
                except asyncio.CancelledError:
                    logger.info(f"Worker {self.worker_id} cancelled")
                    break
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error: {str(e)}")
            self.running = False

    def stop(self) -> None:
        """Stop the worker."""
        self.running = False
        logger.info(f"Worker {self.worker_id} stopped")


async def run_workers(num_workers: int = 2) -> asyncio.Task | None:
    """Run multiple workers processing tasks from the queue.

    Args:
        num_workers: Number of concurrent workers to run

    Returns:
        A task that runs all workers (can be used with asyncio.create_task)
    """
    workers = [TaskWorker(worker_id=i) for i in range(num_workers)]

    async def run_all_workers():
        """Run all workers concurrently."""
        await asyncio.gather(*[worker.start() for worker in workers])

    return asyncio.create_task(run_all_workers())
