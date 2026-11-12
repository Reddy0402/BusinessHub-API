"""Tests for the AI Smart Task Assistant.

The real OpenRouter API is never called: complete_json() is replaced with a fake
that returns a canned answer, so CI stays free, fast and needs no API key.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from app import ai
from app.main import app
from app.store import store

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    store.clear()
    yield
    store.clear()


@pytest.fixture
def fake_ai(monkeypatch):
    """Make the AI return `fake_ai.answer` and record the prompts it was sent."""

    class Fake:
        answer: dict = {}
        calls: list = []

    fake = Fake()
    fake.calls = []

    def complete_json(system_prompt, user_prompt):
        fake.calls.append((system_prompt, user_prompt))
        if isinstance(fake.answer, Exception):
            raise fake.answer
        return fake.answer

    monkeypatch.setattr(ai, "complete_json", complete_json)
    return fake


# ---------- parse-task ----------
def test_parse_task_creates_task(fake_ai):
    fake_ai.answer = {
        "title": "Finish client report",
        "description": "Send to the client",
        "priority": "HIGH",
        "due_date": "2099-03-06",
    }
    response = client.post("/ai/parse-task", json={"text": "Finish client report by Friday, urgent"})

    assert response.status_code == 200
    body = response.json()
    assert body["created"] is True
    assert body["task"]["title"] == "Finish client report"
    assert body["task"]["priority"] == "high"
    assert body["task"]["due_date"] == "2099-03-06"
    assert client.get("/tasks").json() == [body["task"]]
    assert "Finish client report by Friday, urgent" in fake_ai.calls[0][1]


def test_parse_task_draft_only_does_not_save(fake_ai):
    fake_ai.answer = {"title": "Call bank", "priority": "low", "due_date": None}
    body = client.post("/ai/parse-task", json={"text": "call bank", "create": False}).json()

    assert body["created"] is False
    assert body["task"] is None
    assert body["draft"]["title"] == "Call bank"
    assert client.get("/tasks").json() == []


def test_parse_task_cleans_bad_values(fake_ai):
    fake_ai.answer = {"title": "", "priority": "super-urgent", "due_date": "next friday"}
    body = client.post("/ai/parse-task", json={"text": "water the plants"}).json()

    assert body["task"]["title"] == "water the plants"  # falls back to the user's text
    assert body["task"]["priority"] == "medium"
    assert body["task"]["due_date"] is None


def test_parse_task_rejects_empty_text(fake_ai):
    assert client.post("/ai/parse-task", json={"text": ""}).status_code == 422
    assert fake_ai.calls == []


def test_parse_task_ai_error_returns_503(fake_ai):
    fake_ai.answer = ai.AIError("The free AI model is busy (rate limit).", 503)
    response = client.post("/ai/parse-task", json={"text": "anything"})

    assert response.status_code == 503
    assert "busy" in response.json()["detail"]
    assert client.get("/tasks").json() == []


# ---------- insights ----------
def test_insights_without_tasks_skips_ai(fake_ai):
    body = client.get("/ai/insights").json()

    assert body["summary"] == "You have no tasks yet."
    assert body["analytics"]["total_tasks"] == 0
    assert fake_ai.calls == []


def test_insights_uses_analytics(fake_ai):
    client.post("/tasks", json={"title": "Old bug", "priority": "high", "due_date": "2020-01-01"})
    client.post("/tasks", json={"title": "Done thing", "status": "completed"})
    fake_ai.answer = {"summary": "1 of 2 tasks done.", "suggestions": ["Fix Old bug first", ""]}

    body = client.get("/ai/insights").json()

    assert body["summary"] == "1 of 2 tasks done."
    assert body["suggestions"] == ["Fix Old bug first"]
    assert body["analytics"]["overdue_tasks"] == 1
    assert "Old bug" in fake_ai.calls[0][1] and "OVERDUE" in fake_ai.calls[0][1]


# ---------- breakdown ----------
def test_breakdown_saves_subtasks(fake_ai):
    task_id = client.post("/tasks", json={"title": "Launch website"}).json()["id"]
    fake_ai.answer = {"subtasks": ["Buy domain", "Build pages", "Deploy"]}

    response = client.post(f"/ai/breakdown/{task_id}")

    assert response.status_code == 201
    assert [s["title"] for s in response.json()] == ["Buy domain", "Build pages", "Deploy"]
    assert client.get(f"/tasks/{task_id}/subtasks").json() == response.json()


def test_breakdown_unknown_task_returns_404(fake_ai):
    assert client.post("/ai/breakdown/999").status_code == 404
    assert fake_ai.calls == []


def test_breakdown_bad_answer_returns_502(fake_ai):
    task_id = client.post("/tasks", json={"title": "Something"}).json()["id"]
    fake_ai.answer = {"steps": "not a list"}

    assert client.post(f"/ai/breakdown/{task_id}").status_code == 502
    assert store.list_subtasks(task_id) == []


# ---------- the OpenRouter client itself (HTTP is faked) ----------
def test_client_without_key_is_not_configured():
    with pytest.raises(ai.AIError) as err:
        ai.complete_json("system", "user")
    assert err.value.status_code == 503


def test_client_reads_json_from_fenced_reply(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    sent = {}

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, headers=headers, body=json)
        reply = '```json\n{"title": "Hi"}\n```'
        return httpx.Response(200, json={"choices": [{"message": {"content": reply}}]})

    monkeypatch.setattr(ai.httpx, "post", fake_post)

    assert ai.complete_json("system", "user") == {"title": "Hi"}
    assert sent["url"] == ai.OPENROUTER_URL
    assert sent["headers"]["Authorization"] == "Bearer test-key"
    assert sent["body"]["model"] == ai.DEFAULT_MODELS[0]
    assert sent["body"]["models"] == ai.DEFAULT_MODELS


def test_model_list_can_be_configured(monkeypatch):
    monkeypatch.setenv("OPENROUTER_MODEL", " a/one:free , b/two:free ,")
    assert ai.model_list() == ["a/one:free", "b/two:free"]
    assert ai.model_name() == "a/one:free"


def test_client_maps_rate_limit_to_503(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(ai.httpx, "post", lambda *a, **k: httpx.Response(429, json={}))

    with pytest.raises(ai.AIError) as err:
        ai.complete_json("system", "user")
    assert err.value.status_code == 503
