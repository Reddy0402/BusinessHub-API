"""Tests for GET /greet/{name}."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_greet_normal_name():
    response = client.get("/greet/Sai")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Sai!"}


def test_greet_single_letter():
    response = client.get("/greet/A")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, A!"}


def test_greet_name_with_spaces():
    response = client.get("/greet/John%20Doe")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, John Doe!"}


def test_greet_name_with_special_characters():
    response = client.get("/greet/Marie-Curie")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Marie-Curie!"}


def test_greet_missing_name_returns_404():
    response = client.get("/greet/")
    assert response.status_code == 404


def test_greet_name_too_long_returns_422():
    response = client.get("/greet/" + "A" * 101)
    assert response.status_code == 422
