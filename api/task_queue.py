import asyncio
from collections.abc import Callable
from enum import Enum

from .models import Task


class TaskEvent(str, Enum):
    """Events that can be published from workers."""

    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


class TaskQueue:
    """In-memory task queue with async support."""

    def __init__(self):
        self._queue: asyncio.Queue[Task] = asyncio.Queue()
        self._callbacks: dict[TaskEvent, list[Callable]] = {event: [] for event in TaskEvent}

    async def enqueue(self, task: Task) -> None:
        """Add a task to the queue."""
        await self._queue.put(task)

    async def dequeue(self) -> Task:
        """Get the next task from the queue."""
        return await self._queue.get()

    async def size(self) -> int:
        """Get the current queue size."""
        return self._queue.qsize()

    def subscribe(self, event: TaskEvent, callback: Callable) -> None:
        """Subscribe to task events."""
        self._callbacks[event].append(callback)

    async def publish(self, event: TaskEvent, task: Task) -> None:
        """Publish a task event."""
        for callback in self._callbacks[event]:
            if asyncio.iscoroutinefunction(callback):
                await callback(task)
            else:
                callback(task)


# Global task queue instance
task_queue = TaskQueue()
