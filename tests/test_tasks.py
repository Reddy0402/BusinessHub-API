"""Tests for the task API backed by the database store."""

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal, TaskRow
from app.main import app
from app.store import store

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    store.clear()
    yield
    store.clear()


def test_create_and_get_task():
    created = client.post("/tasks", json={"title": "  Write report  ", "priority": "high", "due_date": "2099-01-31"})
    assert created.status_code == 201
    task = created.json()
    assert task == {
        "id": task["id"],
        "title": "Write report",
        "description": None,
        "priority": "high",
        "status": "pending",
        "due_date": "2099-01-31",
    }
    assert client.get(f"/tasks/{task['id']}").json() == task
    assert client.get("/tasks").json() == [task]


def test_update_task_and_completed_at():
    task_id = client.post("/tasks", json={"title": "Ship it"}).json()["id"]

    done = client.put(f"/tasks/{task_id}", json={"status": "completed", "description": "today"})
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    assert done.json()["description"] == "today"
    with SessionLocal() as session:
        assert session.get(TaskRow, task_id).completed_at is not None

    reopened = client.put(f"/tasks/{task_id}", json={"status": "pending"})
    assert reopened.json()["status"] == "pending"
    with SessionLocal() as session:
        assert session.get(TaskRow, task_id).completed_at is None


def test_delete_task_removes_its_subtasks():
    task_id = client.post("/tasks", json={"title": "Big job"}).json()["id"]
    store.add_subtasks(task_id, ["step one", "step two"])
    assert len(client.get(f"/tasks/{task_id}/subtasks").json()) == 2

    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404
    assert store.list_subtasks(task_id) == []


def test_missing_task_returns_404():
    assert client.get("/tasks/999").status_code == 404
    assert client.put("/tasks/999", json={"title": "x"}).status_code == 404
    assert client.delete("/tasks/999").status_code == 404
    assert client.get("/tasks/999/subtasks").status_code == 404


def test_validation_errors():
    assert client.post("/tasks", json={"title": "   "}).status_code == 422
    assert client.post("/tasks", json={"title": "ok", "titel": "typo"}).status_code == 422
    assert client.post("/tasks", json={"title": "ok", "priority": "urgent"}).status_code == 422
