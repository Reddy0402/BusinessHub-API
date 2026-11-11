"""Tests for GET /health."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    """Health returns status ok and version from version.txt."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_version_matches_version_txt():
    """The /health version equals the contents of app/version.txt."""
    from pathlib import Path

    expected = Path("app/version.txt").read_text(encoding="utf-8").strip() or "dev"
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == expected
