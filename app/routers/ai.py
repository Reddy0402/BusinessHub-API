"""AI Smart Task Assistant endpoints (OpenRouter, free models).

  POST /ai/parse-task           plain English -> a structured (and saved) task
  GET  /ai/insights             analytics -> short productivity summary + suggestions
  POST /ai/breakdown/{task_id}  split a task into saved subtasks

Everything the model returns is validated before it is used or stored.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app import ai
from app.routers.analytics import Analytics, get_analytics
from app.store import Priority, Status, Subtask, Task, TaskCreate, store

router = APIRouter(prefix="/ai", tags=["ai"])

MAX_SUBTASKS = 8


class ParseTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1, max_length=500, description="The task in plain English")
    create: bool = Field(True, description="Save the task (true) or only return the draft (false)")


class ParseTaskResponse(BaseModel):
    created: bool
    draft: TaskCreate
    task: Optional[Task] = None


class InsightsResponse(BaseModel):
    summary: str
    suggestions: list[str]
    analytics: Analytics


def _call_ai(endpoint: str, system_prompt: str, user_prompt: str, log_text: str) -> dict:
    try:
        result = ai.complete_json(system_prompt, user_prompt)
    except ai.AIError as err:
        raise HTTPException(status_code=err.status_code, detail=err.message)
    try:
        store.log_ai_call(endpoint, log_text, ai.model_name())
    except Exception:
        pass  # usage logging must never break the feature
    return result


def _bad_answer() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="The AI returned an answer that could not be used. Please try again.",
    )


# ---------- POST /ai/parse-task ----------
PARSE_SYSTEM_PROMPT = """You turn a short task description into JSON for a task tracker.
Reply with ONLY a JSON object, no other text, using exactly these keys:
  "title": short task title (max 100 characters),
  "description": extra details from the text, or null,
  "priority": "low", "medium" or "high" (urgent/asap/important -> "high"; default "medium"),
  "due_date": the due date as "YYYY-MM-DD", or null if no date is mentioned.
Resolve relative dates such as "tomorrow" or "Friday" using today's date."""


def _clean_draft(data: dict, original_text: str) -> TaskCreate:
    title = str(data.get("title") or "").strip() or original_text.strip()
    description = data.get("description")
    description = str(description).strip()[:1000] if description else None

    priority = str(data.get("priority") or "medium").strip().lower()
    if priority not in {p.value for p in Priority}:
        priority = Priority.medium.value

    due_date = None
    raw_due = data.get("due_date")
    if raw_due:
        try:
            due_date = date.fromisoformat(str(raw_due).strip()[:10])
        except ValueError:
            due_date = None

    try:
        return TaskCreate(
            title=title[:200], description=description or None, priority=priority, due_date=due_date
        )
    except ValidationError:
        raise _bad_answer()


@router.post("/parse-task", response_model=ParseTaskResponse)
def parse_task(payload: ParseTaskRequest):
    """Create a task from plain English, e.g. "Finish client report by Friday, urgent"."""
    today = date.today()
    user_prompt = f"Today is {today.isoformat()} ({today.strftime('%A')}).\nTask: {payload.text}"
    data = _call_ai("parse-task", PARSE_SYSTEM_PROMPT, user_prompt, payload.text)
    draft = _clean_draft(data, payload.text)

    if not payload.create:
        return ParseTaskResponse(created=False, draft=draft)
    return ParseTaskResponse(created=True, draft=draft, task=store.add(draft))


# ---------- GET /ai/insights ----------
INSIGHTS_SYSTEM_PROMPT = """You are a friendly productivity coach for a task tracker.
You get task statistics and a list of open tasks. Reply with ONLY a JSON object:
  "summary": 1-2 sentences describing the user's progress, using the numbers,
  "suggestions": a list of 2-4 short, concrete next actions (mention task titles when useful).
Prioritise overdue and high-priority tasks."""


@router.get("/insights", response_model=InsightsResponse)
def insights():
    """A short AI summary of your productivity plus suggested next steps."""
    stats = get_analytics()
    if stats.total_tasks == 0:
        # Nothing to analyse - don't spend an AI call on it.
        return InsightsResponse(
            summary="You have no tasks yet.",
            suggestions=["Add your first task to get personalised insights."],
            analytics=stats,
        )

    today = date.today()
    open_tasks = [t for t in store.list() if t.status == Status.pending]
    open_tasks.sort(key=lambda t: (t.due_date or date.max, ["high", "medium", "low"].index(t.priority.value)))
    lines = []
    for task in open_tasks[:15]:
        due = ""
        if task.due_date:
            due = f", due {task.due_date.isoformat()}" + (" (OVERDUE)" if task.due_date < today else "")
        lines.append(f"- {task.title} [{task.priority.value} priority{due}]")

    user_prompt = (
        f"Today is {today.isoformat()}.\n"
        f"Statistics: {stats.model_dump_json()}\n"
        f"Open tasks:\n" + ("\n".join(lines) or "(none)")
    )
    data = _call_ai("insights", INSIGHTS_SYSTEM_PROMPT, user_prompt, None)

    summary = str(data.get("summary") or "").strip()
    suggestions = data.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = [suggestions]
    suggestions = [str(s).strip()[:300] for s in suggestions if str(s).strip()][:5]
    if not summary:
        raise _bad_answer()
    return InsightsResponse(summary=summary[:1000], suggestions=suggestions, analytics=stats)


# ---------- POST /ai/breakdown/{task_id} ----------
BREAKDOWN_SYSTEM_PROMPT = f"""You split a task into small, concrete steps.
Reply with ONLY a JSON object: {{"subtasks": ["step 1", "step 2", ...]}}
Give 3 to {MAX_SUBTASKS - 2} steps, each a short action (max 100 characters), in a sensible order."""


@router.post("/breakdown/{task_id}", response_model=list[Subtask], status_code=status.HTTP_201_CREATED)
def breakdown(task_id: int = Path(..., ge=1, description="ID of the task")):
    """Ask the AI to split a task into subtasks and save them."""
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")

    user_prompt = f"Task: {task.title}"
    if task.description:
        user_prompt += f"\nDetails: {task.description}"
    data = _call_ai("breakdown", BREAKDOWN_SYSTEM_PROMPT, user_prompt, task.title)

    steps = data.get("subtasks")
    if not isinstance(steps, list):
        raise _bad_answer()
    titles = [str(step).strip()[:200] for step in steps if str(step).strip()][:MAX_SUBTASKS]
    if not titles:
        raise _bad_answer()
    return store.add_subtasks(task_id, titles)
