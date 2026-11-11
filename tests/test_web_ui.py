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
