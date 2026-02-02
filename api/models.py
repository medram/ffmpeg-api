from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskRegisterRequest(BaseModel):
    """Request to register a new FFmpeg task.

    New payload must include:
    - `ffmpeg_command`: the ffmpeg command string
    - `input_files`: mapping of input keys (like `in_1`) to URLs
    - `output_files`: mapping of output keys (like `out_1`) to filenames

    Legacy fields `command` and `output_filename` are not accepted.
    """

    ffmpeg_command: str = Field(..., description="FFmpeg command arguments (required)")
    input_files: dict[str, str] = Field(..., description="Dict mapping input keys to URLs")
    output_files: dict[str, str] = Field(..., description="Dict mapping output keys to filenames")

    class Config:
        extra = "forbid"


class TaskResponse(BaseModel):
    """Response containing task information."""

    task_id: str
    status: TaskStatus
    output_urls: dict[str, str] | None = None
    error_message: str | None = None


class Task:
    """In-memory task storage."""

    def __init__(
        self,
        task_id: str,
        command: str,
        input_files: dict[str, str],
        output_files: dict[str, str],
    ):
        self.task_id = task_id
        self.command = command
        self.input_files = input_files
        self.output_files = output_files

        self.status = TaskStatus.PENDING
        self.output_urls: dict[str, str] | None = None
        self.error_message: str | None = None

    def to_response(self) -> TaskResponse:
        return TaskResponse(
            task_id=self.task_id,
            status=self.status,
            output_urls=self.output_urls,
            error_message=self.error_message,
        )
