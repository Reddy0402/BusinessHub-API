# BusinessHub-API — Complete Project Explanation

**Repository:** `D:\teamapi\BusinessHub-API`
**Branch:** `feature/businesshub-mcp` (work done locally; not pushed unless requested)
**Status:** Feature complete locally. All 48 tests pass (33 existing + 15 MCP). MCP integration complete locally; not committed, pushed, or deployed.

---

## 1. Project Overview

BusinessHub-API (branded as **TeamTask**) is a small production-style FastAPI task-tracker API built for a CI/CD workshop. It demonstrates the full pipeline:

```
branch → PR → GitHub Actions CI → merge to main → deploy → smoke test
```

The app is a single-container Python service backed by **Supabase PostgreSQL** via SQLAlchemy (with an in-memory SQLite fallback for local tests when `DATABASE_URL` is unset). It includes task management, productivity analytics, an AI Smart Task Assistant (OpenRouter free models), a vanilla HTML/JS frontend, and a **Model Context Protocol (MCP) server** mounted at `/mcp`.

---

## 2. Architecture

### Layering

| Layer | Responsibility | Key files |
|-------|---------------|-----------|
| Entry point | FastAPI app creation, health check, static file serving, router registration, MCP mount | `app/main.py` |
| Database | SQLAlchemy engine, session, table definitions (Supabase Postgres / SQLite fallback) | `app/db.py` |
| Shared model + store | Task schema, enum types, database-backed `TaskStore` singleton | `app/store.py` |
| Task router | CRUD endpoints under `/tasks` | `app/routers/tasks.py` |
| Analytics router | Productivity statistics under `/analytics` | `app/routers/analytics.py` |
| AI router | OpenRouter-backed parse-task / insights / breakdown under `/ai` | `app/routers/ai.py` |
| MCP server | MCP tools mounted at `/mcp`, calling the existing store layer | `app/mcp/server.py`, `app/mcp/tools.py` |
| Frontend | Single-page HTML/JS UI calling the API via relative `fetch()` | `app/static/index.html` |
| Tests | pytest test files, one per feature | `tests/` |

### Design decisions (from `app/store.py`)

- **Single shared store instance** (`store = TaskStore()`) imported by every router and the MCP tools, so they always see the same tasks persisted to the same database.
- **Database-backed:** `TaskStore` uses SQLAlchemy `SessionLocal` from `app/db.py`. In production it connects to Supabase PostgreSQL via `DATABASE_URL`; in tests/CI it falls back to an in-memory SQLite database.
- **MCP reuses the existing store layer** — no second SQLAlchemy engine, no second database, no duplicated business logic, and no HTTP calls back into the REST API.

---

## 3. MCP Server Integration

### Transport and endpoint

| Item | Value |
|------|-------|
| SDK | Official MCP Python SDK v2 |
| Package | `mcp==2.3.0` |
| Transport | Streamable HTTP |
| Endpoint | `http://127.0.0.1:8000/mcp` (local) |
| Intended production endpoint | `https://businesshub-api-production.up.railway.app/mcp` |

The MCP server is created with `mcp.server.mcpserver.MCPServer` (the v2 replacement for the removed v1 `FastMCP`) and exposed as a Starlette ASGI app via `streamable_http_app()`. It is mounted into the **existing** FastAPI application:

```python
app.mount("/mcp", mcp_app)
```

The MCP StreamableHTTP session manager's lifecycle is driven once by `mcp_lifespan`, used as the FastAPI application lifespan.

### MCP tools (12 registered)

All tools call the existing BusinessHub store/service layer (`app/store.py`) — they never duplicate SQL, never create a second database connection, and never call the REST API over HTTP.

| # | Tool | Reads / Writes | Description |
|---|------|----------------|-------------|
| 1 | `businesshub_health` | Read | Health / version (equivalent to `GET /health`). Does not touch the database. |
| 2 | `list_tasks` | Read | List all tasks (equivalent to `GET /tasks`). |
| 3 | `get_task` | Read | Get one task by id (equivalent to `GET /tasks/{id}`). Clean error if not found. |
| 4 | `list_subtasks` | Read | List a task's subtasks (equivalent to `GET /tasks/{id}/subtasks`). |
| 5 | `get_analytics` | Read | Productivity analytics (equivalent to `GET /analytics`). Reuses existing calculation. |
| 6 | `get_business_info` | Read | BusinessHub information (equivalent to `GET /info`). |
| 7 | `create_task` | **Write** | Create a task (equivalent to `POST /tasks`). Modifies persistent Supabase data. |
| 8 | `update_task` | **Write** | Update a task (equivalent to `PUT /tasks/{id}`). Modifies persistent Supabase data. |
| 9 | `delete_task` | **Write** | Delete a task (equivalent to `DELETE /tasks/{id}`). Modifies persistent Supabase data. |
| 10 | `parse_task` | **Write** (when `create=true`) | Parse plain English into a task via the existing OpenRouter AI layer; optionally saves. |
| 11 | `get_ai_insights` | Read | AI productivity summary via the existing OpenRouter AI layer. |
| 12 | `breakdown_task` | **Write** | Split a task into subtasks via the existing AI layer; saves via `store.add_subtasks()`. |

Read-only tools never modify Supabase data. Write tools create or modify persistent BusinessHub/Supabase data through the existing store layer.

### Database architecture (MCP data path)

```text
MCP tool
  ↓
app/mcp/tools.py
  ↓
app/store.py  (TaskStore singleton)
  ↓
app/db.py     (SQLAlchemy SessionLocal / engine)
  ↓
SQLAlchemy
  ↓
Supabase PostgreSQL
```

MCP does **NOT** create:

- a second database
- a second SQLAlchemy engine
- duplicated business logic
- HTTP calls back into the REST API

### Session handling

The MCP implementation uses **stateful Streamable HTTP**. The session lifecycle is:

```text
initialize
    ↓
server returns mcp-session-id
    ↓
client sends mcp-session-id on subsequent requests
    ↓
session manager routes the request to the correct MCP session
```

A normal browser request such as `GET /mcp` is **not** a valid MCP protocol test:

- `GET /mcp` returns a `307 Temporary Redirect` to `/mcp/`.
- A direct `GET /mcp/` without a valid `mcp-session-id` header returns JSON-RPC error `-32600 Missing session ID`.

This is correct MCP protocol behavior and is **not** an MCP implementation failure. A real MCP client (e.g. MCP Inspector or the official MCP Python SDK client) must perform the `initialize` handshake, capture the `mcp-session-id`, and include it on subsequent `tools/list` and `tools/call` requests.

---

## 4. File Structure

```
BusinessHub-API/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, /health, /, router registration, MCP mount
│   ├── version.txt             # Version string ("dev" locally; commit SHA in prod)
│   ├── db.py                   # SQLAlchemy engine, SessionLocal, table definitions
│   ├── store.py                # Shared Task models + database-backed TaskStore singleton
│   ├── mcp/
│   │   ├── __init__.py         # MCP package entry point
│   │   ├── server.py           # v2 MCPServer, Streamable HTTP app, mcp_lifespan
│   │   └── tools.py            # 12 MCP tools calling the existing store layer
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── tasks.py            # CRUD: POST/GET/PUT/DELETE /tasks
│   │   ├── analytics.py        # GET /analytics productivity stats
│   │   ├── ai.py               # POST /ai/parse-task, GET /ai/insights, POST /ai/breakdown/{id}
│   │   ├── conflict_demo.py    # GET /conflict-demo
│   │   ├── info.py             # GET /info
│   │   └── sai_status.py       # GET /sai/status
│   └── static/
│       └── index.html          # Browser UI: task manager + analytics dashboard + AI assistant
├── tests/
│   ├── conftest.py             # SQLite fallback, empty AI key (test setup)
│   ├── test_health.py          # /health tests
│   ├── test_tasks.py           # Task CRUD tests
│   ├── test_analytics.py       # Analytics endpoint tests
│   ├── test_ai.py              # AI endpoint tests (OpenRouter faked)
│   ├── test_web_ui.py          # Frontend serving tests
│   └── test_mcp.py             # MCP protocol tests (15 tests)
├── docs/
│   ├── PROJECT-EXPLANATION.md  # This file (NEW/UPDATED)
│   └── CONFLICT-RESOLUTION.md  # Merge-conflict exercise documentation (NEW)
├── requirements.txt            # fastapi, uvicorn, pydantic, sqlalchemy, psycopg, mcp, ...
├── requirements-dev.txt        # + pytest
├── Dockerfile                  # python:3.12-slim, listens on 0.0.0.0:$PORT (unchanged)
├── .github/workflows/ci.yml    # PR to main: pytest + docker build
├── .github/workflows/deploy.yml # Push to main: test → deploy → smoke test
├── .env.example                # Supabase DATABASE_URL, OpenRouter keys (not committed)
├── .gitignore                  # Excludes .env, venv, __pycache__, etc.
├── README.md                   # Usage and feature documentation (includes MCP section)
└── LICENSE                     # Apache License 2.0
```

---

## 5. Core Components

### 5.1 `app/store.py` — Shared Task Model & Store

**Enums:**
- `Priority`: `low`, `medium`, `high`
- `Status`: `pending`, `completed`

**Pydantic models:**
- `TaskCreate` — body for `POST /tasks`. Only `title` required. Defaults: `priority=medium`, `status=pending`, `due_date=None`.
- `TaskUpdate` — body for `PUT /tasks/{id}`. Partial updates; at least one field required; `title`/`priority`/`status` cannot be nulled.
- `Task` — stored task returned by the API: `id`, `title`, `description`, `priority`, `status`, `due_date`.
- `Subtask` — subtask: `id`, `task_id`, `title`, `status`.

**`TaskStore` class:**
- `list()` → all tasks
- `get(id)` → single task or `None`
- `add(data)` → create and return task with auto-incremented `id`
- `update(id, changes)` → apply partial changes, return updated task or `None`
- `delete(id)` → `bool`
- `list_subtasks(id)` → subtasks for a task
- `add_subtasks(id, titles)` → create subtasks
- `log_ai_call(...)` → record AI usage in `ai_logs`
- `clear()` → empty store (tests only; refuses to run against a real database)

**Global instance:** `store = TaskStore()` — imported by all routers and MCP tools.

### 5.2 `app/main.py` — Application Entry Point

- Loads `.env` for local development (before `app.db` import).
- Creates the FastAPI app (title: "TeamTask API") with `lifespan=mcp_lifespan`.
- `read_version()` reads `app/version.txt`, falls back to `"dev"` if missing/empty.
- `GET /health` → `{"status": "ok", "version": "..."}` — does not touch the database or AI.
- `GET /` → serves `app/static/index.html` as `FileResponse`.
- Registers all feature routers (`tasks`, `analytics`, `conflict_demo`, `info`, `ai`, `sai_status`).
- Mounts the MCP Starlette app at `/mcp`.

```python
app.include_router(tasks.router)
app.include_router(analytics.router)
app.include_router(conflict_demo.router)
app.include_router(info.router)
app.include_router(ai.router)
app.include_router(sai_status.router)

# --- MCP endpoint (streamable-http) ---
app.mount("/mcp", mcp_app)
```

### 5.3 `app/mcp/server.py` — MCP Server Initialization

- Creates `MCPServer(name="businesshub", ...)` (v2 SDK).
- Registers all 12 tools via `mcp_server.add_tool(...)`.
- Builds `mcp_app = mcp_server.streamable_http_app(streamable_http_path="/", transport_security=...)`.
- Exposes `mcp_lifespan` which runs `session_manager.run()` exactly once.
- DNS rebinding protection is disabled for this prototype so the endpoint works on localhost and on the production Railway domain; auth/transport security can be enabled later.

### 5.4 `app/mcp/tools.py` — MCP Tool Definitions

Every tool calls `app/store.py` methods (`store.list`, `store.get`, `store.add`, `store.update`, `store.delete`, `store.list_subtasks`, `store.add_subtasks`) or the existing AI layer (`app/ai.complete_json`). No SQL is duplicated. No credentials are exposed in tool descriptions or responses.

---

## 6. API Endpoints Summary

| Method | Path | Success | Description |
|--------|------|---------|-------------|
| `GET` | `/health` | `200` `{"status":"ok","version":"..."}` | Liveness check |
| `GET` | `/` | `200` `text/html` | Serves the browser UI |
| `POST` | `/tasks` | `201` the created task | Create a task |
| `GET` | `/tasks` | `200` list of tasks | List all tasks |
| `GET` | `/tasks/{id}` | `200` the task | Get one task |
| `PUT` | `/tasks/{id}` | `200` updated task | Partial update |
| `DELETE` | `/tasks/{id}` | `204` no body | Delete a task |
| `GET` | `/tasks/{id}/subtasks` | `200` list of subtasks | List subtasks |
| `GET` | `/analytics` | `200` analytics summary | Productivity stats |
| `GET` | `/info` | `200` info message | BusinessHub information |
| `GET` | `/conflict-demo` | `200` demo message | Conflict demo endpoint |
| `GET` | `/sai/status` | `200` status message | Sai feature status |
| `POST` | `/ai/parse-task` | `200` parsed task | AI: parse text into task |
| `GET` | `/ai/insights` | `200` insights | AI: productivity summary |
| `POST` | `/ai/breakdown/{id}` | `201` subtasks | AI: split task into subtasks |
| — | `/mcp` | MCP protocol | Streamable HTTP MCP endpoint |

Interactive docs: `http://localhost:8000/docs`

---

## 7. Testing

Run with: `python -m pytest -v`

### Test files

- **`tests/conftest.py`** — Sets `DATABASE_URL` to in-memory SQLite and empties AI keys before tests; never uses production credentials.
- **`tests/test_health.py`** (4 tests) — `/health` status/version behavior.
- **`tests/test_tasks.py`** (5 tests) — Task CRUD including subtask cleanup on delete.
- **`tests/test_analytics.py`** (6 tests) — Analytics calculations and edge cases.
- **`tests/test_ai.py`** (9 tests) — AI endpoints with OpenRouter faked (no real API calls).
- **`tests/test_web_ui.py`** (4 tests) — Frontend serving.
- **`tests/test_mcp.py`** (15 tests) — MCP protocol: server init, endpoint exists, client connect, tools/list, read/write tools, not-found errors, REST still works.

### Verified result

```text
Existing tests: 33 passed
MCP tests: 15 passed
Total: 48 passed
```

### Real MCP protocol verification (live server)

The MCP protocol flow was verified against the running uvicorn server at `http://127.0.0.1:8000/mcp` using raw MCP JSON-RPC over Streamable HTTP:

| Step | Result |
|------|--------|
| `initialize` | PASS — session established, `mcp-session-id` returned |
| `tools/list` | PASS — all 12 tools visible |
| `tools/call` (`businesshub_health`) | PASS — read tool returned `{"status": "ok", "version": "dev"}` |
| `tools/call` (`create_task`) | PASS — write tool created a task persisted via `store.add()` |
| `tools/call` (`list_tasks`) | PASS — confirmed the created task is visible |

---

## 8. How to Run Locally

### Prerequisites
Python 3.12, `pip`, optionally Docker.

### Run directly (PowerShell)

```powershell
# 1. Create and activate virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies (dev includes pytest)
pip install -r requirements-dev.txt

# 3. Run tests
python -m pytest -v

# 4. Start the server
uvicorn app.main:app --reload
```

Then open **http://localhost:8000/** for the UI, or call:
- `curl http://localhost:8000/health`
- `curl http://localhost:8000/tasks`
- `curl http://localhost:8000/docs`
- MCP endpoint: `http://localhost:8000/mcp` (use MCP Inspector or MCP SDK client, not a browser GET)

### Docker

The `Dockerfile` is unchanged and uses `python:3.12-slim`, installing from `requirements.txt` (which now includes `mcp==2.3.0`). The container listens on `0.0.0.0` and port `${PORT:-8000}` (Railway-compatible).

```powershell
docker build -t businesshub-api-mcp .
docker run --rm -p 8000:8000 businesshub-api-mcp
```

> Docker build was not executed in the current verification environment because the Docker daemon was unavailable. The Dockerfile itself remains unchanged.

---

## 9. CI/CD (GitHub Actions)

### `.github/workflows/ci.yml`
Runs on pull requests to `main`:
1. Checkout → Python 3.12 → install dev deps → `pytest` → Docker build.
2. Fails if tests or Docker build fail.

### `.github/workflows/deploy.yml`
Runs on push to `main`:
1. **Test:** checkout → Python 3.12 → install dev deps → `pytest`.
2. **Deploy:** write `github.sha` to `app/version.txt` → deploy to Railway via `railway up`.
3. **Smoke test:** curl `$APP_URL/health` with retries, verifying `status == "ok"` and `version == $GITHUB_SHA`.

### Version mechanism
- Locally: `version.txt` usually absent → `/health` returns `"dev"`.
- In production: deploy pipeline writes the commit SHA into `app/version.txt`.

---

## 10. Current Repository Status

| Item | Status |
|------|--------|
| Branch | `feature/businesshub-mcp` |
| MCP implementation | Complete locally |
| Tests | 48 passed |
| Commit | Not yet created |
| Push | Not yet performed |
| Deployment | Not yet performed |

> Do not commit, push, create a PR, or deploy unless explicitly requested.

---

## 11. Important Constraints (from AGENTS.md)

- No direct feature development on `main`; use feature branches.
- Every feature needs tests; run `pytest` before opening a PR.
- Do not commit secrets, API keys, or `.env` files.
- Do not push or deploy unless explicitly requested.
- Do not modify unrelated features in a single PR.
- Do not create commits or push unless instructed.

**This explanation file was updated locally and has NOT been committed or pushed.**
