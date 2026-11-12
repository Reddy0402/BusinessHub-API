"""Tests for the browser app served at GET /."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_web_ui_is_served():
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<title>TeamTask</title>" in response.text


def test_web_ui_is_not_listed_in_api_docs():
    assert "/" not in client.get("/openapi.json").json()["paths"]


def test_web_ui_contains_analytics_dashboard():
    """The rendered web app includes the productivity analytics dashboard."""
    response = client.get("/")
    assert response.status_code == 200
    text = response.text
    assert "Productivity analytics" in text
    assert "Total Tasks" in text
    assert "Completed" in text
    assert "Pending" in text
    assert "Overdue" in text
    assert "Completion" in text
    assert "Tasks by Priority" in text
    assert "High" in text
    assert "Medium" in text
    assert "Low" in text
    # The frontend calls the relative analytics endpoint.
    assert "/analytics" in text
