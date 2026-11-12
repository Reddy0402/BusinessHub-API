from fastapi import APIRouter, HTTPException, Path, status

from app.store import Status, Task, store

router = APIRouter(prefix="/tasks", tags=["task actions"])


def _set_status(task_id: int, new_status: Status) -> Task:
    task = store.update(task_id, {"status": new_status})
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")
    return task


@router.post("/{task_id}/complete", response_model=Task)
def complete_task(task_id: int = Path(..., ge=1)):
    """Mark a task as completed."""
    return _set_status(task_id, Status.completed)


@router.post("/{task_id}/reopen", response_model=Task)
def reopen_task(task_id: int = Path(..., ge=1)):
    """Move a task back to pending."""
    return _set_status(task_id, Status.pending)