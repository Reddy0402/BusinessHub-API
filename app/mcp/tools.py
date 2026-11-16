"""MCP tool definitions for BusinessHub.

Every tool calls the existing BusinessHub business/data layer (app.store),
never duplicating SQL queries and never creating a second database connection.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional

from app.ai import AIError, complete_json
from app.db import SessionLocal, TaskRow
from app.routers.ai import BREAKDOWN_SYSTEM_PROMPT, PARSE_SYSTEM_PROMPT, _clean_draft
from app.routers.analytics import Analytics, TasksByPriority, get_analytics as _router_get_analytics
from app.store import (
    Priority,
    Status,
    Subtask,
    Task,
    TaskCreate,
    TaskUpdate,
    store,
)

# Version file mirroring app/main.py so this module never imports app.main
# (avoiding a circular import: main.py mounts the MCP app).
VERSION_FILE = Path(__file__).resolve().parents[1] / "version.txt"


def _read_version() -> str:
    """Return the contents of version.txt, or "dev" if it is missing or empty."""
    try:
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "dev"
    return version or "dev"


# ---------------------------------------------------------------------------
# Helper: convert store models into plain JSON-compatible dicts.
# ---------------------------------------------------------------------------


def _task_to_dict(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority.value if isinstance(task.priority, Enum) else task.priority,
        "status": task.status.value if isinstance(task.status, Enum) else task.status,
        "due_date": task.due_date.isoformat() if task.due_date else None,
    }


def _subtask_to_dict(subtask: Subtask) -> dict[str, Any]:
    return {
        "id": subtask.id,
        "task_id": subtask.task_id,
        "title": subtask.title,
        "status": subtask.status.value if isinstance(subtask.status, Enum) else subtask.status,
    }


def _analytics_to_dict(analytics: Analytics) -> dict[str, Any]:
    return {
        "total_tasks": analytics.total_tasks,
        "completed_tasks": analytics.completed_tasks,
        "pending_tasks": analytics.pending_tasks,
        "overdue_tasks": analytics.overdue_tasks,
        "completion_percentage": analytics.completion_percentage,
        "tasks_by_priority": {
            "high": analytics.tasks_by_priority.high,
            "medium": analytics.tasks_by_priority.medium,
            "low": analytics.tasks_by_priority.low,
        },
    }


# ---------------------------------------------------------------------------
# Read-only tools
# ---------------------------------------------------------------------------


def businesshub_health() -> dict[str, Any]:
    """Return the current BusinessHub health/version information.

    Equivalent to GET /health. Does not touch the database.
    """
    return {"status": "ok", "version": _read_version()}


def list_tasks() -> list[dict[str, Any]]:
    """Return all tasks from the BusinessHub task store.

    Equivalent to GET /tasks.
    """
    tasks = store.list()
    return [_task_to_dict(task) for task in tasks]


def get_task(task_id: int) -> dict[str, Any]:
    """Return one BusinessHub task by id.

    Equivalent to GET /tasks/{task_id}.

    Raises ToolError with a clean message if the task does not exist.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    task = store.get(task_id)
    if task is None:
        raise ToolError(f"Task with id {task_id} does not exist.")
    return _task_to_dict(task)


def list_subtasks(task_id: int) -> list[dict[str, Any]]:
    """Return the subtasks of a BusinessHub task.

    Equivalent to GET /tasks/{task_id}/subtasks.

    Raises ToolError with a clean message if the task does not exist.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    if store.get(task_id) is None:
        raise ToolError(f"Task with id {task_id} does not exist.")
    subtasks = store.list_subtasks(task_id)
    return [_subtask_to_dict(subtask) for subtask in subtasks]


def get_analytics() -> dict[str, Any]:
    """Return BusinessHub productivity analytics.

    Equivalent to GET /analytics. Reuses the existing analytics calculation
    in app/routers/analytics.py.
    """
    analytics = _router_get_analytics()
    return _analytics_to_dict(analytics)


def get_business_info() -> dict[str, Any]:
    """Return BusinessHub information.

    Equivalent to GET /info.
    """
    return {"message": "Team API information"}


# ---------------------------------------------------------------------------
# Write tools (modify Supabase data through the existing store)
# ---------------------------------------------------------------------------


def create_task(
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    status: str = "pending",
    due_date: Optional[date] = None,
) -> dict[str, Any]:
    """Create a new BusinessHub task.

    Equivalent to POST /tasks. This is a WRITE operation that creates
    persistent BusinessHub/Supabase data.

    Fields follow the existing TaskCreate model: title is required,
    priority/status default to medium/pending.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    try:
        payload = TaskCreate(
            title=title,
            description=description,
            priority=Priority(priority) if priority else Priority.medium,
            status=Status(status) if status else Status.pending,
            due_date=due_date,
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc

    task = store.add(payload)
    return _task_to_dict(task)


def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    due_date: Optional[date] = None,
) -> dict[str, Any]:
    """Update an existing BusinessHub task.

    Equivalent to PUT /tasks/{task_id}. This is a WRITE operation that
    modifies persistent BusinessHub/Supabase data.

    Only the fields provided are changed. Sends at least one field to update.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    changes: dict[str, Any] = {}
    if title is not None:
        changes["title"] = title
    if description is not None:
        changes["description"] = description
    if priority is not None:
        changes["priority"] = Priority(priority).value
    if status is not None:
        changes["status"] = Status(status).value
    if due_date is not None:
        changes["due_date"] = due_date

    if not changes:
        raise ToolError("Send at least one field to update.")

    try:
        task = store.update(task_id, changes)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc

    if task is None:
        raise ToolError(f"Task with id {task_id} does not exist.")
    return _task_to_dict(task)


def delete_task(task_id: int) -> dict[str, Any]:
    """Delete a BusinessHub task by id.

    Equivalent to DELETE /tasks/{task_id}. This is a destructive WRITE
    operation that removes persistent BusinessHub/Supabase data (and its
    subtasks).

    Raises ToolError with a clean message if the task does not exist.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    if not store.delete(task_id):
        raise ToolError(f"Task with id {task_id} does not exist.")
    return {"deleted": True, "id": task_id}


# ---------------------------------------------------------------------------
# Optional AI tools (call the existing AI layer, never expose credentials)
# ---------------------------------------------------------------------------


def parse_task(text: str, create: bool = True) -> dict[str, Any]:
    """Parse plain English into a structured BusinessHub task draft.

    Equivalent to POST /ai/parse-task. Calls the existing AI layer
    (OpenRouter free models). When create is true, the task is saved.

    This is a WRITE operation when create=true: it creates persistent
    BusinessHub/Supabase data.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    today = date.today()
    user_prompt = f"Today is {today.isoformat()} ({today.strftime('%A')}).\nTask: {text}"

    try:
        data = complete_json(PARSE_SYSTEM_PROMPT, user_prompt)
    except AIError as exc:
        raise ToolError(exc.message) from exc

    try:
        draft = _clean_draft(data, text)
    except Exception as exc:  # pragma: no cover - defensive
        raise ToolError("The AI returned an answer that could not be used.") from exc

    if not create:
        return {"created": False, "draft": _task_create_to_dict(draft)}

    task = store.add(draft)
    return {"created": True, "draft": _task_create_to_dict(draft), "task": _task_to_dict(task)}


def get_ai_insights() -> dict[str, Any]:
    """Return an AI productivity summary plus suggested next actions.

    Equivalent to GET /ai/insights. Calls the existing AI layer and reuses
    the existing analytics calculation.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    analytics = _router_get_analytics()
    if analytics.total_tasks == 0:
        return {
            "summary": "You have no tasks yet.",
            "suggestions": ["Add your first task to get personalised insights."],
            "analytics": _analytics_to_dict(analytics),
        }

    today = date.today()
    open_tasks = [t for t in store.list() if t.status == Status.pending]
    open_tasks.sort(
        key=lambda t: (
            t.due_date or date.max,
            ["high", "medium", "low"].index(t.priority.value),
        )
    )
    lines = []
    for task in open_tasks[:15]:
        due = ""
        if task.due_date:
            due = f", due {task.due_date.isoformat()}" + (
                " (OVERDUE)" if task.due_date < today else ""
            )
        lines.append(f"- {task.title} [{task.priority.value} priority{due}]")

    user_prompt = (
        f"Today is {today.isoformat()}.\n"
        f"Statistics: {analytics.model_dump_json()}\n"
        f"Open tasks:\n" + ("\n".join(lines) or "(none)")
    )

    try:
        data = complete_json(
            "You are a friendly productivity coach for a task tracker.\n"
            "You get task statistics and a list of open tasks. Reply with ONLY a JSON object:\n"
            '  "summary": 1-2 sentences describing the user\'s progress, using the numbers,\n'
            '  "suggestions": a list of 2-4 short, concrete next actions (mention task titles when useful).\n'
            "Prioritise overdue and high-priority tasks.",
            user_prompt,
        )
    except AIError as exc:
        raise ToolError(exc.message) from exc

    summary = str(data.get("summary") or "").strip()
    suggestions = data.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = [suggestions]
    suggestions = [str(s).strip()[:300] for s in suggestions if str(s).strip()][:5]
    if not summary:
        raise ToolError("The AI returned an answer that could not be used.")

    return {
        "summary": summary[:1000],
        "suggestions": suggestions,
        "analytics": _analytics_to_dict(analytics),
    }


def breakdown_task(task_id: int) -> list[dict[str, Any]]:
    """Split a BusinessHub task into subtasks and save them.

    Equivalent to POST /ai/breakdown/{task_id}. Calls the existing AI layer
    and saves subtasks through the existing store.

    This is a WRITE operation: it creates persistent BusinessHub/Supabase data.
    """
    from mcp.server.mcpserver.exceptions import ToolError

    MAX_SUBTASKS = 8

    task = store.get(task_id)
    if task is None:
        raise ToolError(f"Task with id {task_id} does not exist.")

    user_prompt = f"Task: {task.title}"
    if task.description:
        user_prompt += f"\nDetails: {task.description}"

    try:
        data = complete_json(BREAKDOWN_SYSTEM_PROMPT, user_prompt)
    except AIError as exc:
        raise ToolError(exc.message) from exc

    steps = data.get("subtasks")
    if not isinstance(steps, list):
        raise ToolError("The AI returned an answer that could not be used.")
    titles = [str(step).strip()[:200] for step in steps if str(step).strip()][:MAX_SUBTASKS]
    if not titles:
        raise ToolError("The AI returned an answer that could not be used.")

    subtasks = store.add_subtasks(task_id, titles)
    return [_subtask_to_dict(subtask) for subtask in subtasks]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _task_create_to_dict(draft: TaskCreate) -> dict[str, Any]:
    return {
        "title": draft.title,
        "description": draft.description,
        "priority": draft.priority.value if isinstance(draft.priority, Enum) else draft.priority,
        "due_date": draft.due_date.isoformat() if draft.due_date else None,
    }
