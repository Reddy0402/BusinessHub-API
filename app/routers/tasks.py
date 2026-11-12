"""Task management endpoints (owner: Jaanageswar)."""

from fastapi import APIRouter, HTTPException, Path, Response, status

from app.store import Subtask, Task, TaskCreate, TaskUpdate, store

router = APIRouter(prefix="/tasks", tags=["tasks"])

TaskId = Path(..., ge=1, description="ID of the task")


def _not_found(task_id: int) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate):
    """Create a task. Returns 201 with the new task, including its id."""
    return store.add(payload)


@router.get("", response_model=list[Task])
def list_tasks():
    """Return all tasks."""
    return store.list()


@router.get("/{task_id}", response_model=Task)
def get_task(task_id: int = TaskId):
    """Return one task, or 404 if it does not exist."""
    task = store.get(task_id)
    if task is None:
        raise _not_found(task_id)
    return task


@router.put("/{task_id}", response_model=Task)
def update_task(payload: TaskUpdate, task_id: int = TaskId):
    """Update a task's details or status. Fields you leave out keep their current value."""
    task = store.update(task_id, payload.model_dump(exclude_unset=True))
    if task is None:
        raise _not_found(task_id)
    return task


@router.get("/{task_id}/subtasks", response_model=list[Subtask])
def list_subtasks(task_id: int = TaskId):
    """Return the subtasks of a task (created by POST /ai/breakdown/{task_id})."""
    if store.get(task_id) is None:
        raise _not_found(task_id)
    return store.list_subtasks(task_id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int = TaskId):
    """Delete a task. Returns 204 with no body, or 404 if it does not exist."""
    if not store.delete(task_id):
        raise _not_found(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
