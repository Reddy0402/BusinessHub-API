"""Tests for GET /subtract?a=5&b=3."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_subtract_numbers():
    response = client.get("/subtract?a=5&b=3")

    assert response.status_code == 200
    assert response.json()["result"] == 2


def test_subtract_gives_negative_result():
    response = client.get("/subtract?a=2&b=5")

    assert response.status_code == 200
    assert response.json()["result"] == -3


def test_subtract_decimal_numbers():
    response = client.get("/subtract?a=5.5&b=2.25")

    assert response.status_code == 200
    assert response.json()["result"] == 3.25


def test_subtract_missing_parameter_returns_422():
    response = client.get("/subtract?a=5")

    assert response.status_code == 422
