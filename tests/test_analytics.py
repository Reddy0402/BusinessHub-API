"""Tests for GET /analytics.

Analytics values are computed dynamically from the shared in-memory task
store, so each test creates tasks through the real task API and then checks
the analytics endpoint.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import store

client = TestClient(app)

PAST_DUE = date(2020, 1, 1)   # always in the past -> overdue if pending
FUTURE_DUE = date(2099, 12, 31)  # always in the future -> not overdue


@pytest.fixture(autouse=True)
def reset_store():
    """Start every test with an empty store and leave it empty afterwards."""
    store.clear()
    yield
    store.clear()


def _create_task(title, priority="medium", status="pending", due_date=None):
    payload = {"title": title, "priority": priority}
    if status:
        payload["status"] = status
    if due_date is not None:
        payload["due_date"] = due_date.isoformat()
    return client.post("/tasks", json=payload)


def test_analytics_empty_task_list():
    """No tasks: every count is zero and completion percentage is 0.0."""
    response = client.get("/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "total_tasks": 0,
        "completed_tasks": 0,
        "pending_tasks": 0,
        "overdue_tasks": 0,
        "completion_percentage": 0.0,
        "tasks_by_priority": {"high": 0, "medium": 0, "low": 0},
    }


def test_analytics_all_tasks_completed():
    """All tasks completed: completion percentage is 100.0, nothing pending."""
    _create_task("Done high", priority="high", status="completed")
    _create_task("Done low", priority="low", status="completed", due_date=PAST_DUE)

    response = client.get("/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 2
    assert data["completed_tasks"] == 2
    assert data["pending_tasks"] == 0
    # Completed tasks are not overdue even with a past due date.
    assert data["overdue_tasks"] == 0
    assert data["completion_percentage"] == 100.0
    assert data["tasks_by_priority"] == {"high": 1, "medium": 0, "low": 1}


def test_analytics_mixed_completed_and_pending():
    response = client.get("/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 0  # store was reset by the fixture

    _create_task("Pending high", priority="high", status="pending")
    _create_task("Pending medium", priority="medium", status="pending")
    _create_task("Completed low", priority="low", status="completed")

    response = client.get("/analytics")
    data = response.json()
    assert data["total_tasks"] == 3
    assert data["completed_tasks"] == 1
    assert data["pending_tasks"] == 2
    assert data["overdue_tasks"] == 0
    assert data["completion_percentage"] == 33.33
    assert data["tasks_by_priority"] == {"high": 1, "medium": 1, "low": 1}


def test_analytics_overdue_task_calculation():
    """Overdue = pending task with a due date before today."""
    _create_task("Overdue pending", priority="high", status="pending", due_date=PAST_DUE)
    _create_task("Overdue but completed", priority="medium", status="completed", due_date=PAST_DUE)
    _create_task("Not overdue future", priority="low", status="pending", due_date=FUTURE_DUE)
    _create_task("No due date", priority="low", status="pending")

    response = client.get("/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 4
    assert data["pending_tasks"] == 3
    assert data["completed_tasks"] == 1
    assert data["overdue_tasks"] == 1
    assert data["tasks_by_priority"] == {"high": 1, "medium": 1, "low": 2}


def test_analytics_completion_percentage():
    _create_task("A", status="completed")
    _create_task("B", status="completed")
    _create_task("C", status="completed")
    _create_task("D", status="pending")
    _create_task("E", status="pending")

    response = client.get("/analytics")
    data = response.json()
    assert data["total_tasks"] == 5
    assert data["completed_tasks"] == 3
    assert data["pending_tasks"] == 2
    #this is changed line to create the conflict in this line
    assert data["completion_percentage"] == 99.0


def test_analytics_zero_task_division_safety():
    """The store is empty: no division-by-zero, percentage is 0.0."""
    response = client.get("/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 0
    assert data["completion_percentage"] == 0.0
    assert data["tasks_by_priority"] == {"high": 0, "medium": 0, "low": 0}
