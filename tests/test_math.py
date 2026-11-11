from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_add_numbers():
    response = client.get("/add?a=2&b=3")

    assert response.status_code == 200
    assert response.json()["result"] == 5


def test_add_negative_numbers():
    response = client.get("/add?a=-2&b=5")

    assert response.status_code == 200
    assert response.json()["result"] == 3


def test_add_decimal_numbers():
    response = client.get("/add?a=2.5&b=3.5")

    assert response.status_code == 200
    assert response.json()["result"] == 6
