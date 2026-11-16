"""Tests for the BusinessHub MCP server.

These tests exercise the real MCP protocol (Streamable HTTP transport) against
the mounted MCP endpoint on the main FastAPI app at /mcp, using the official
MCP Python SDK patterns (JSON-RPC over Streamable HTTP). The tests use the
in-memory test database (SQLite, via tests/conftest.py), so no production
Supabase database and no real credentials are required.

A single TestClient is shared across all tests so the MCP session manager's
lifespan (session_manager.run()) is entered exactly once via mcp_lifespan.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.mcp.server import mcp_server
from app.store import TaskCreate, store

# Mount path used in app/main.py.
MOUNT_PATH = "/mcp"

# REST client for the REST-alongside-MCP check.
rest_client = TestClient(app)

# Shared MCP client across the whole test session: enters the app lifespan
# (and therefore mcp_lifespan -> session_manager.run()) exactly once.
_mcp_client = TestClient(app)
_mcp_client.__enter__()
# Track the MCP session id returned by the server so stateful requests reuse it.
_mcp_session_id: str | None = None


@pytest.fixture(autouse=True)
def _reset_store():
    store.clear()
    yield
    store.clear()


# ---------------------------------------------------------------------------
# MCP request helpers (real Streamable HTTP JSON-RPC protocol).
# ---------------------------------------------------------------------------


def _mcp_request(method: str, params: dict[str, Any] | None = None, request_id: int = 1) -> dict[str, Any]:
    """Send one MCP JSON-RPC request to /mcp via ASGI (Streamable HTTP)."""
    global _mcp_session_id
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if _mcp_session_id:
        headers["mcp-session-id"] = _mcp_session_id

    response = _mcp_client.post(
        MOUNT_PATH,
        content=json.dumps(payload),
        headers=headers,
    )
    assert response.status_code == 200, f"{method} failed: {response.status_code} {response.text}"

    # Capture the session id the server assigns (stateful mode).
    session_id = response.headers.get("mcp-session-id")
    if session_id:
        _mcp_session_id = session_id

    # The Streamable HTTP transport responds with SSE by default:
    # `event: message\ndata: <json>\n\n`. Extract the JSON from the data field.
    body = response.text
    parsed = None
    for line in body.splitlines():
        if line.startswith("data: "):
            parsed = json.loads(line[len("data: "):])
            break
    if parsed is None:
        # Fallback: plain JSON body.
        parsed = response.json()
    return parsed


def _mcp_initialize() -> None:
    """Perform the MCP initialize handshake."""
    result = _mcp_request(
        "initialize",
        {
            "protocolVersion": "2026-07-28",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"},
        },
        request_id=1,
    )
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == 1
    assert "result" in result, f"initialize failed: {result}"


def _mcp_list_tools() -> list[dict[str, Any]]:
    result = _mcp_request("tools/list", request_id=2)
    assert "result" in result, f"tools/list failed: {result}"
    return result["result"]["tools"]


def _mcp_call_tool(name: str, arguments: dict[str, Any] | None = None, request_id: int = 3) -> dict[str, Any]:
    result = _mcp_request(
        "tools/call",
        {"name": name, "arguments": arguments or {}},
        request_id=request_id,
    )
    assert "result" in result, f"tools/call {name} failed: {result}"
    return result["result"]


# ---------------------------------------------------------------------------
# Test helpers for creating tasks through the existing store.
# ---------------------------------------------------------------------------


def _mk_task(title: str, **kwargs) -> dict[str, Any]:
    """Create a task through the existing store and return a JSON-compatible dict."""
    task = store.add(TaskCreate(title=title, **kwargs))
    return _task_dict(task)


def _task_dict(task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority.value,
        "status": task.status.value,
        "due_date": task.due_date.isoformat() if task.due_date else None,
    }


# ---------------------------------------------------------------------------
# Extract helpers for MCP CallToolResult.
# ---------------------------------------------------------------------------


def _extract_text(result: dict[str, Any]) -> str:
    contents = result.get("content") or []
    for block in contents:
        if block.get("type") == "text":
            return block.get("text", "")
    return ""


def _extract_data(result: dict[str, Any]) -> Any:
    structured = result.get("structured_content")
    if structured is None:
        # The MCP wire format serialises the field as camelCase "structuredContent".
        structured = result.get("structuredContent")
    if structured is not None:
        data = structured
        # MCP wraps list/dict returns in {"result": ...} (structured_output).
        if isinstance(data, dict) and "result" in data and len(data) == 1:
            return data["result"]
        return data
    text = _extract_text(result)
    return json.loads(text) if text else None


def _extract_data_list(result: dict[str, Any]) -> list[Any]:
    data = _extract_data(result)
    return data if isinstance(data, list) else [data]


# ---------------------------------------------------------------------------
# A. MCP server initializes.
# B. MCP endpoint exists.
# C. MCP client can connect.
# D. MCP tool listing works.
# ---------------------------------------------------------------------------


def test_mcp_server_initializes():
    assert mcp_server is not None
    assert mcp_server.name == "businesshub"


def test_mcp_endpoint_exists():
    paths = [getattr(route, "path", None) for route in app.router.routes]
    assert "/mcp" in paths


def test_mcp_client_can_connect():
    _mcp_initialize()


def test_mcp_tool_listing_works():
    _mcp_initialize()
    tools = _mcp_list_tools()
    names = [t["name"] for t in tools]
    expected = [
        "businesshub_health",
        "list_tasks",
        "get_task",
        "list_subtasks",
        "get_analytics",
        "get_business_info",
        "create_task",
        "update_task",
        "delete_task",
        "parse_task",
        "get_ai_insights",
        "breakdown_task",
    ]
    for name in expected:
        assert name in names, f"Tool {name!r} not listed: {names}"


# ---------------------------------------------------------------------------
# E. businesshub_health works.
# F. list_tasks works.
# G. get_task works.
# H. get_analytics works.
# ---------------------------------------------------------------------------


def test_businesshub_health():
    _mcp_initialize()
    result = _mcp_call_tool("businesshub_health", request_id=10)
    data = _extract_data(result)
    assert data["status"] == "ok"
    assert isinstance(data["version"], str) and data["version"]


def test_list_tasks():
    _mcp_initialize()
    _mk_task("Task one")
    _mk_task("Task two")

    result = _mcp_call_tool("list_tasks", request_id=20)
    tasks = _extract_data_list(result)
    assert len(tasks) == 2
    titles = {t["title"] for t in tasks}
    assert titles == {"Task one", "Task two"}


def test_get_task():
    _mcp_initialize()
    created = _mk_task("Get me", priority="high", due_date="2099-01-31")

    result = _mcp_call_tool("get_task", {"task_id": created["id"]}, request_id=30)
    task = _extract_data(result)
    assert task["id"] == created["id"]
    assert task["title"] == "Get me"
    assert task["priority"] == "high"
    assert task["status"] == "pending"
    assert task["due_date"] == "2099-01-31"


def test_get_analytics():
    _mcp_initialize()
    _mk_task("Done task", status="completed")
    _mk_task("Pending task")

    result = _mcp_call_tool("get_analytics", request_id=40)
    analytics = _extract_data(result)
    assert analytics["total_tasks"] == 2
    assert analytics["completed_tasks"] == 1
    assert analytics["pending_tasks"] == 1
    assert analytics["completion_percentage"] == 50.0


# ---------------------------------------------------------------------------
# I. create_task works (write).
# J. update_task works.
# K. delete_task works.
# ---------------------------------------------------------------------------


def test_create_task():
    _mcp_initialize()

    result = _mcp_call_tool(
        "create_task",
        {"title": "MCP created task", "priority": "high", "due_date": "2099-03-01"},
        request_id=50,
    )
    task = _extract_data(result)
    assert task["title"] == "MCP created task"
    assert task["priority"] == "high"
    assert task["status"] == "pending"
    assert task["due_date"] == "2099-03-01"
    assert task["id"] >= 1

    # Persisted through the existing store.
    fetched = store.get(task["id"])
    assert fetched is not None
    assert fetched.title == "MCP created task"


def test_update_task():
    _mcp_initialize()
    created = _mk_task("To update")

    result = _mcp_call_tool(
        "update_task",
        {"task_id": created["id"], "status": "completed", "title": "Updated title"},
        request_id=60,
    )
    task = _extract_data(result)
    assert task["status"] == "completed"
    assert task["title"] == "Updated title"


def test_delete_task():
    _mcp_initialize()
    created = _mk_task("To delete")

    result = _mcp_call_tool("delete_task", {"task_id": created["id"]}, request_id=70)
    data = _extract_data(result)
    assert data["deleted"] is True
    assert data["id"] == created["id"]

    assert store.get(created["id"]) is None


# ---------------------------------------------------------------------------
# L. list_subtasks works.
# ---------------------------------------------------------------------------


def test_list_subtasks():
    _mcp_initialize()
    created = _mk_task("Parent task")
    store.add_subtasks(created["id"], ["step one", "step two"])

    result = _mcp_call_tool("list_subtasks", {"task_id": created["id"]}, request_id=80)
    subtasks = _extract_data_list(result)
    assert len(subtasks) == 2
    titles = {s["title"] for s in subtasks}
    assert titles == {"step one", "step two"}


# ---------------------------------------------------------------------------
# M. Invalid task IDs return clean errors.
# ---------------------------------------------------------------------------


def test_get_task_not_found_clean_error():
    _mcp_initialize()

    result = _mcp_call_tool("get_task", {"task_id": 999999}, request_id=90)
    assert result.get("isError") is True
    content = _extract_text(result)
    assert "does not exist" in content


def test_delete_task_not_found_clean_error():
    _mcp_initialize()

    result = _mcp_call_tool("delete_task", {"task_id": 999999}, request_id=91)
    assert result.get("isError") is True


# ---------------------------------------------------------------------------
# N. Existing REST endpoints still work alongside /mcp.
# ---------------------------------------------------------------------------


def test_rest_endpoints_still_work():
    response = rest_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    response = rest_client.post("/tasks", json={"title": "REST task"})
    assert response.status_code == 201
    task = response.json()
    assert task["title"] == "REST task"

    response = rest_client.get(f"/tasks/{task['id']}")
    assert response.status_code == 200
