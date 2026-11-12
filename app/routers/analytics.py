"""Productivity analytics endpoints (owner: Sai).

Reads live task data from the shared store and returns summary statistics:
total, completed, pending and overdue task counts, completion percentage,
and the number of tasks per priority.

Overdue tasks are pending tasks whose due_date is in the past. Completed
tasks are never counted as overdue, even if their due_date has passed.
"""

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.store import Priority, Status, store

router = APIRouter(prefix="/analytics", tags=["analytics"])


class TasksByPriority(BaseModel):
    """Task counts grouped by priority."""

    high: int = Field(default=0, ge=0)
    medium: int = Field(default=0, ge=0)
    low: int = Field(default=0, ge=0)


class Analytics(BaseModel):
    """Summary statistics computed from the current task data."""

    total_tasks: int = Field(ge=0)
    completed_tasks: int = Field(ge=0)
    pending_tasks: int = Field(ge=0)
    overdue_tasks: int = Field(ge=0)
    completion_percentage: float = Field(ge=0.0, le=100.0)
    tasks_by_priority: TasksByPriority


@router.get("", response_model=Analytics)
def get_analytics():
    """Return productivity analytics computed from the shared task store."""

    tasks = store.list()

    total = len(tasks)
    completed = sum(1 for task in tasks if task.status == Status.completed)
    pending = total - completed

    today = date.today()
    overdue = sum(
        1
        for task in tasks
        if task.status == Status.pending
        and task.due_date is not None
        and task.due_date < today
    )

    # No division by zero: with no tasks the completion percentage is 0.0.
    completion_percentage = round((completed / total) * 100, 2) if total else 0.0

    tasks_by_priority = TasksByPriority(
        high=sum(1 for task in tasks if task.priority == Priority.high),
        medium=sum(1 for task in tasks if task.priority == Priority.medium),
        low=sum(1 for task in tasks if task.priority == Priority.low),
    )

    return Analytics(
        total_tasks=total,
        completed_tasks=completed,
        pending_tasks=pending,
        overdue_tasks=overdue,
        completion_percentage=completion_percentage,
        tasks_by_priority=tasks_by_priority,
    )
