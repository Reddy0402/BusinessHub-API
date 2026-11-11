"""Tests for GET /reverse/{text}."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_reverse_normal():
    response = client.get("/reverse/hello")
    assert response.status_code == 200
    assert response.json() == {"result": "olleh"}


def test_reverse_single_char():
    response = client.get("/reverse/a")
    assert response.status_code == 200
    assert response.json() == {"result": "a"}


def test_reverse_palindrome():
    response = client.get("/reverse/racecar")
    assert response.status_code == 200
    assert response.json() == {"result": "racecar"}


def test_reverse_spaces():
    response = client.get("/reverse/hello%20world")
    assert response.status_code == 200
    assert response.json() == {"result": "dlrow olleh"}


def test_reverse_empty_string():
    response = client.get("/reverse/")
    assert response.status_code == 404
