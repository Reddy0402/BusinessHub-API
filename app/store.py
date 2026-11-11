"""Shared task model and in-memory task store.

Both features use this module:
  * Task management (app/routers/tasks.py)      - Jaanageswar
  * Productivity analytics (app/routers/analytics.py) - Sai

Because they import the same `store` object, they always see the same tasks.

Design decision: there is no database on purpose. Data lives in a Python
dictionary, so it is lost when the app restarts. That keeps the workshop
focused on CI/CD and is fine for a single container.
"""

from datetime import date
from enum import Enum
from threading import Lock
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# A title is trimmed of surrounding spaces and must not be empty.
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Status(str, Enum):
    pending = "pending"
    completed = "completed"


class TaskCreate(BaseModel):
    """Body for POST /tasks. Only `title` is required."""

    model_config = ConfigDict(extra="forbid")  # reject unknown fields, e.g. a typo like "titel"

    title: Title
    description: Optional[Description] = None
    priority: Priority = Priority.medium
    status: Status = Status.pending
    # Past dates are allowed on purpose: analytics needs to find overdue tasks.
    due_date: Optional[date] = None


class TaskUpdate(BaseModel):
    """Body for PUT /tasks/{id}. Send only the fields you want to change."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[Title] = None
    description: Optional[Description] = None
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    due_date: Optional[date] = None

    @model_validator(mode="after")
    def check_fields(self):
        if not self.model_fields_set:
            raise ValueError("Send at least one field to update")
        # description and due_date may be cleared with null; these may not.
        for field in ("title", "priority", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"'{field}' cannot be null")
        return self


class Task(BaseModel):
    """A stored task, as returned by the API."""

    id: int = Field(..., ge=1)
    title: Title
    description: Optional[Description] = None
    priority: Priority
    status: Status
    due_date: Optional[date] = None


class TaskStore:
    """A tiny in-memory store. A lock keeps IDs unique if two requests arrive at once."""

    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._next_id = 1
        self._lock = Lock()

    def list(self) -> list[Task]:
        with self._lock:
            return list(self._tasks.values())

    def get(self, task_id: int) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def add(self, data: TaskCreate) -> Task:
        with self._lock:
            task = Task(id=self._next_id, **data.model_dump())
            self._tasks[task.id] = task
            self._next_id += 1
            return task

    def update(self, task_id: int, changes: dict) -> Optional[Task]:
        with self._lock:
            current = self._tasks.get(task_id)
            if current is None:
                return None
            updated = current.model_copy(update=changes)
            self._tasks[task_id] = updated
            return updated

    def delete(self, task_id: int) -> bool:
        with self._lock:
            return self._tasks.pop(task_id, None) is not None

    def clear(self) -> None:
        """Remove every task and restart IDs at 1 (handy in tests)."""
        with self._lock:
            self._tasks.clear()
            self._next_id = 1


# The single shared store used by every router.
store = TaskStore()
