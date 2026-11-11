"""Tests for GET /add?a=2&b=3."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_add_positive():
    response = client.get("/add?a=2&b=3")
    assert response.status_code == 200
    assert response.json() == {"result": 5}


def test_add_negative():
    response = client.get("/add?a=-5&b=3")
    assert response.status_code == 200
    assert response.json() == {"result": -2}


def test_add_zero():
    response = client.get("/add?a=0&b=0")
    assert response.status_code == 200
    assert response.json() == {"result": 0}


def test_add_large_numbers():
    response = client.get("/add?a=1000000&b=2000000")
    assert response.status_code == 200
    assert response.json() == {"result": 3000000}


def test_add_missing_parameter_returns_422():
    response = client.get("/add?a=2")
    assert response.status_code == 422
