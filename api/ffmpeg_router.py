import asyncio
import os
import tempfile
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from utils import get_file_manager

from .ffmpeg_executor import FFmpegExecutor
from .models import Task, TaskRegisterRequest, TaskResponse
from .task_queue import task_queue

api = APIRouter()

# Global task storage
_tasks: dict[str, Task] = {}


# Pydantic model for merge-audio-video endpoint
class MergeAudioVideoRequest(BaseModel):
    video_url: str = Field(..., description="URL of the loop video (mp4) or local filename")
    audio_urls: list[str] = Field(..., description="List of audio URLs (mp3) to concatenate")
    output_filename: str | None = Field(None, description="Output video filename")


@api.post("/merge-audio-video")
async def merge_audio_video(request: MergeAudioVideoRequest) -> TaskResponse:
    """Create a long YouTube-style music video by merging audio URLs and a loop video."""
    work_dir = tempfile.mkdtemp()
    file_manager = get_file_manager()
    video_local = await file_manager.download_file(request.video_url, "loop_video.mp4")

    audio_files = []
    for i, url in enumerate(request.audio_urls):
        fname = f"track_{i:03d}.mp3"
        audio_files.append(await file_manager.download_file(url, fname))

    concat_list_path = os.path.join(work_dir, "concat.txt")
    with open(concat_list_path, "w") as f:
        for af in audio_files:
            f.write(f"file '{os.path.abspath(af)}'\n")
    merged_audio = os.path.join(work_dir, "merged_audio.mp3")

    # Create the concat command to merge audio files
    concat_cmd = f"ffmpeg -y -f concat -safe 0 -i {concat_list_path} -c copy {merged_audio}"
    proc = await asyncio.create_subprocess_shell(
        concat_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()

    # Get duration of merged audio to set video length
    probe_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {merged_audio}"
    proc = await asyncio.create_subprocess_shell(
        probe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, _ = await proc.communicate()
    duration = float(out.decode().strip())
    output_filename = request.output_filename or "output.mp4"
    output_path = os.path.join(work_dir, output_filename)
    merge_cmd = (
        f"ffmpeg -y -stream_loop -1 -i {video_local} -i {merged_audio} "
        f"-map 0:v -map 1:a -shortest -c:v libx264 -preset fast -crf 18 "
        f"-c:a aac -b:a 192k -t {duration} {output_path}"
    )
    # Run the merge command
    proc = await asyncio.create_subprocess_shell(
        merge_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    # Check if FFmpeg succeeded and output file exists
    if proc.returncode != 0 or not os.path.exists(output_path):
        error_detail = err.decode() if err else out.decode()
        file_manager.cleanup()
        raise HTTPException(
            status_code=500, detail=f"FFmpeg failed to create output file: {error_detail}"
        )

    # Upload to S3
    s3_key = f"youtube-merge/{uuid.uuid4()}/{output_filename}"
    url = file_manager.upload_to_s3(output_path, s3_key)

    # Cleanup temporary files
    file_manager.cleanup()

    return TaskResponse(
        task_id=s3_key,
        status="completed",
        output_urls={"video": url},
        error_message=None,
    )


@api.post("/register")
async def register_task(request: TaskRegisterRequest) -> TaskResponse:
    """Register a new FFmpeg task and enqueue it for processing.

    The task will be automatically picked up by background workers
    and processed asynchronously.

    Args:
        request: Task registration request containing command, input files, and output filename

    Returns:
        TaskResponse with task_id and status (always 'pending')
    """
    task_id = str(uuid.uuid4())

    # New API: only support `ffmpeg_command` and `output_files`.
    cmd = request.ffmpeg_command
    ofiles = request.output_files

    # Pydantic `TaskRegisterRequest` enforces presence; still include runtime checks.
    if not cmd:
        raise HTTPException(status_code=400, detail="No ffmpeg_command provided")
    if not ofiles:
        raise HTTPException(status_code=400, detail="No output_files provided")

    task = Task(
        task_id=task_id,
        command=cmd,
        input_files=request.input_files,
        output_files=ofiles,
    )
    # Store task in memory
    _tasks[task_id] = task

    # Enqueue task for background processing
    await task_queue.enqueue(task)

    return task.to_response()


@api.get("/status/{task_id}")
async def check_task_status(task_id: str) -> TaskResponse:
    """Check the status of a FFmpeg task.

    Args:
        task_id: ID of the task to check

    Returns:
        TaskResponse with current status and output URL if completed

    Raises:
        HTTPException: If task not found
    """
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = _tasks[task_id]
    return task.to_response()


@api.get("/queue/size")
async def get_queue_size() -> dict[str, int]:
    """Get the current size of the task queue.

    Returns:
        Queue size
    """
    size = await task_queue.size()
    return {"queue_size": size}


@api.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Health status
    """
    ffmpeg_installed = FFmpegExecutor.check_ffmpeg_installed()
    return {
        "status": "ok",
        "ffmpeg_installed": "yes" if ffmpeg_installed else "no",
    }
