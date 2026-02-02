import uuid

from fastapi import APIRouter, HTTPException

from .ffmpeg_executor import FFmpegExecutor
from .models import Task, TaskRegisterRequest, TaskResponse
from .task_queue import task_queue

api = APIRouter()

# Global task storage
_tasks: dict[str, Task] = {}


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
