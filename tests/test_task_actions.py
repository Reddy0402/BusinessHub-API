from fastapi.testclient import TestClient

from app.main import app
from app.store import store

client = TestClient(app)


def setup_function():
    store.clear()  # every test starts with an empty task list


def create_task(title="Write tests"):
    return client.post("/tasks", json={"title": title}).json()


def test_complete_task():
    task = create_task()

    response = client.post(f"/tasks/{task['id']}/complete")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert client.get(f"/tasks/{task['id']}").json()["status"] == "completed"


def test_reopen_task():
    task = create_task()
    client.post(f"/tasks/{task['id']}/complete")

    response = client.post(f"/tasks/{task['id']}/reopen")

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_complete_missing_task_returns_404():
    response = client.post("/tasks/999/complete")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task 999 not found"