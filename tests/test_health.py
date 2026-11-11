"""Tests for GET /health."""

from fastapi.testclient import TestClient

import app.main as main
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]


def test_health_reads_version_file(tmp_path, monkeypatch):
    version_file = tmp_path / "version.txt"
    version_file.write_text("abc1234\n", encoding="utf-8")
    monkeypatch.setattr(main, "VERSION_FILE", version_file)

    assert client.get("/health").json() == {"status": "ok", "version": "abc1234"}


def test_health_falls_back_to_dev_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "VERSION_FILE", tmp_path / "does-not-exist.txt")

    assert client.get("/health").json() == {"status": "ok", "version": "dev"}


def test_health_falls_back_to_dev_when_file_empty(tmp_path, monkeypatch):
    version_file = tmp_path / "version.txt"
    version_file.write_text("   \n", encoding="utf-8")
    monkeypatch.setattr(main, "VERSION_FILE", version_file)

    assert client.get("/health").json()["version"] == "dev"
