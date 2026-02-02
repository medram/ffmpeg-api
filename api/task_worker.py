import asyncio
import logging

from .ffmpeg_executor import FFmpegExecutor
from .file_manager import FileManager
from .models import Task, TaskStatus
from .task_queue import TaskEvent, task_queue

logger = logging.getLogger(__name__)


class TaskWorker:
    """Worker that processes tasks from the queue."""

    def __init__(
        self,
        worker_id: int,
        s3_bucket: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str = "us-east-1",
    ):
        self.worker_id = worker_id
        self.s3_bucket = s3_bucket
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.running = False

    def get_file_manager(self) -> FileManager:
        """Create a FileManager instance."""
        return FileManager(
            s3_bucket=self.s3_bucket,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            aws_region=self.aws_region,
        )

    async def process_task(self, task: Task) -> None:
        """Process a single task.

        Args:
            task: The task to process
        """
        logger.info(f"Worker {self.worker_id}: Processing task {task.task_id}")

        task.status = TaskStatus.RUNNING
        await task_queue.publish(TaskEvent.TASK_STARTED, task)

        try:
            file_manager = self.get_file_manager()

            # Download input files
            logger.info(f"Worker {self.worker_id}: Downloading files for {task.task_id}")
            local_files = await file_manager.download_files(task.input_files)

            # Prepare output file path(s) (new API always provides output_files)
            output_local_paths: dict[str, str] = {}
            for out_key, out_name in task.output_files.items():
                output_local_paths[out_key] = file_manager.get_temp_file_path(out_name)

            # Execute FFmpeg command
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

            # Upload output(s) to S3
            logger.info(f"Worker {self.worker_id}: Uploading output for {task.task_id}")
            # Upload all outputs to S3
            task.output_urls = {}
            for out_key, local_path in output_local_paths.items():
                filename = task.output_files.get(out_key, out_key)
                s3_key = f"ffmpeg-outputs/{task.task_id}/{filename}"
                url = file_manager.upload_to_s3(local_path, s3_key)
                task.output_urls[out_key] = url

            task.status = TaskStatus.COMPLETED
            logger.info(f"Worker {self.worker_id}: Task {task.task_id} completed successfully")
            await task_queue.publish(TaskEvent.TASK_COMPLETED, task)

            # Cleanup temporary files
            file_manager.cleanup()

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            logger.error(f"Worker {self.worker_id}: Task {task.task_id} error: {str(e)}")
            await task_queue.publish(TaskEvent.TASK_FAILED, task)

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


async def run_workers(
    num_workers: int = 2,
    s3_bucket: str = "ffmpeg-output",
    aws_access_key_id: str = "",
    aws_secret_access_key: str = "",
    aws_region: str = "us-east-1",
) -> asyncio.Task | None:
    """Run multiple workers processing tasks from the queue.

    Args:
        num_workers: Number of concurrent workers to run
        s3_bucket: S3 bucket for uploads
        aws_access_key_id: AWS access key
        aws_secret_access_key: AWS secret key
        aws_region: AWS region

    Returns:
        A task that runs all workers (can be used with asyncio.create_task)
    """
    workers = [
        TaskWorker(
            worker_id=i,
            s3_bucket=s3_bucket,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
        for i in range(num_workers)
    ]

    async def run_all_workers():
        """Run all workers concurrently."""
        await asyncio.gather(*[worker.start() for worker in workers])

    return asyncio.create_task(run_all_workers())
