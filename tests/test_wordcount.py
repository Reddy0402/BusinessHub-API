"""Tests for POST /wordcount."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_wordcount_normal():
    response = client.post(
        "/wordcount", json={"text": "hello world from BusinessHub"}
    )
    assert response.status_code == 200
    assert response.json() == {"count": 4}


def test_wordcount_single_word():
    response = client.post("/wordcount", json={"text": "hello"})
    assert response.status_code == 200
    assert response.json() == {"count": 1}


def test_wordcount_multiple_spaces():
    response = client.post("/wordcount", json={"text": "a   b    c"})
    assert response.status_code == 200
    assert response.json() == {"count": 3}


def test_wordcount_empty_text():
    response = client.post("/wordcount", json={"text": ""})
    assert response.status_code == 200
    assert response.json() == {"count": 0}


def test_wordcount_missing_text_field():
    response = client.post("/wordcount", json={})
    assert response.status_code == 422
