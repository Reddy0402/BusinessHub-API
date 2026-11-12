"""Shared task models and the database-backed task store.

Every feature uses this module:
  * Task management (app/routers/tasks.py)            - Jaanageswar
  * Productivity analytics (app/routers/analytics.py) - Sai
  * AI Smart Task Assistant (app/routers/ai.py)

Tasks are stored in a database (Supabase Postgres in production, see app/db.py),
so they survive restarts and redeploys. The store keeps the same methods the
original in-memory version had, so the routers did not need to change.
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from sqlalchemy import delete, select

from app.db import AILogRow, SessionLocal, SubtaskRow, TaskRow, is_sqlite

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


class Subtask(BaseModel):
    """A smaller step of a task (created by the AI breakdown feature)."""

    id: int = Field(..., ge=1)
    task_id: int = Field(..., ge=1)
    title: Title
    status: Status


def _value(field):
    """Enum members are stored as their plain string value."""
    return field.value if isinstance(field, Enum) else field


def _to_task(row: TaskRow) -> Task:
    return Task(
        id=row.id,
        title=row.title,
        description=row.description,
        priority=row.priority,
        status=row.status,
        due_date=row.due_date,
    )


def _to_subtask(row: SubtaskRow) -> Subtask:
    return Subtask(id=row.id, task_id=row.task_id, title=row.title, status=row.status)


class TaskStore:
    """Task storage backed by the database configured in app/db.py."""

    def list(self) -> list[Task]:
        with SessionLocal() as session:
            rows = session.scalars(select(TaskRow).order_by(TaskRow.id)).all()
            return [_to_task(row) for row in rows]

    def get(self, task_id: int) -> Optional[Task]:
        with SessionLocal() as session:
            row = session.get(TaskRow, task_id)
            return _to_task(row) if row else None

    def add(self, data: TaskCreate) -> Task:
        values = {key: _value(value) for key, value in data.model_dump().items()}
        with SessionLocal() as session:
            row = TaskRow(**values)
            if row.status == Status.completed.value:
                row.completed_at = datetime.now(timezone.utc)
            session.add(row)
            session.commit()
            return _to_task(row)

    def update(self, task_id: int, changes: dict) -> Optional[Task]:
        with SessionLocal() as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                return None
            was_completed = row.status == Status.completed.value
            for key, value in changes.items():
                setattr(row, key, _value(value))
            is_completed = row.status == Status.completed.value
            if is_completed and not was_completed:
                row.completed_at = datetime.now(timezone.utc)
            elif was_completed and not is_completed:
                row.completed_at = None
            session.commit()
            return _to_task(row)

    def delete(self, task_id: int) -> bool:
        with SessionLocal() as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                return False
            session.delete(row)  # subtasks are deleted with it
            session.commit()
            return True

    # ---------- subtasks ----------
    # Note: inside this class `list` is the method above, so annotations use typing.List.
    def list_subtasks(self, task_id: int) -> List[Subtask]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(SubtaskRow).where(SubtaskRow.task_id == task_id).order_by(SubtaskRow.id)
            ).all()
            return [_to_subtask(row) for row in rows]

    def add_subtasks(self, task_id: int, titles: List[str]) -> List[Subtask]:
        with SessionLocal() as session:
            rows = [SubtaskRow(task_id=task_id, title=title) for title in titles]
            session.add_all(rows)
            session.commit()
            return [_to_subtask(row) for row in rows]

    # ---------- AI usage log ----------
    def log_ai_call(self, endpoint: str, input_text: Optional[str], model: str) -> None:
        with SessionLocal() as session:
            session.add(AILogRow(endpoint=endpoint, input_text=(input_text or "")[:1000], model=model))
            session.commit()

    def clear(self) -> None:
        """Remove every row (tests only). Refuses to run against a real database."""
        if not is_sqlite():
            raise RuntimeError("store.clear() only runs on the SQLite test database")
        with SessionLocal() as session:
            session.execute(delete(SubtaskRow))
            session.execute(delete(TaskRow))
            session.execute(delete(AILogRow))
            session.commit()


# The single shared store used by every router.
store = TaskStore()
