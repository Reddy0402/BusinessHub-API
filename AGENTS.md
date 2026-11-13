# BusinessHub API — Agent Instructions

Python 3.12 FastAPI service. Small production-style API demonstrating CI/CD:
branch → PR → GitHub Actions CI → merge to main → deploy → smoke test.

## Project architecture

- `app/main.py` — FastAPI app (title: "TeamTask API"), `/health`, the web UI at `/`, router registration. Loads `.env` for local dev. No business logic here.
- `app/version.txt` — version string ("dev" locally, Git commit SHA in production). `/health` reads it at runtime; `/health` must never touch the database or the AI.
- `app/db.py` — SQLAlchemy engine + tables (`tasks`, `subtasks`, `ai_logs`). Uses `DATABASE_URL` (Supabase Postgres); falls back to in-memory SQLite when unset.
- `db/schema.sql` — the Postgres schema (source of truth for Supabase, enables RLS).
- `app/store.py` — Pydantic models + the database-backed `store` used by every router. `store.clear()` only runs on SQLite.
- `app/ai.py` — OpenRouter client (`OPENROUTER_API_KEY`, optional `OPENROUTER_MODEL` list of free models).
- `app/routers/tasks.py` — task CRUD + `GET /tasks/{id}/subtasks`
- `app/routers/analytics.py` — `GET /analytics`
- `app/routers/ai.py` — `POST /ai/parse-task`, `GET /ai/insights`, `POST /ai/breakdown/{id}`
- `app/routers/info.py`, `app/routers/conflict_demo.py` — demo endpoints
- `app/static/index.html` — browser UI (tasks, analytics, AI assistant)
- `tests/` — pytest tests. `tests/conftest.py` forces SQLite and an empty AI key; AI tests fake `ai.complete_json`, never the real API.
- `requirements.txt` — production deps (fastapi, uvicorn, sqlalchemy, psycopg, httpx, python-dotenv)
- `requirements-dev.txt` — adds pytest
- `.github/workflows/ci.yml` — runs on PRs to main: pytest + docker build
- `.github/workflows/deploy.yml` — runs on push to main: test → deploy → smoke-test

## Developer commands

Activate venv (PowerShell): `.\.venv\Scripts\Activate.ps1`

Install deps: `pip install -r requirements.txt` (prod) or `pip install -r requirements-dev.txt` (dev+test)

Run all tests: `python -m pytest -v`

Run one test file: `python -m pytest tests/test_health.py -v`

Run server locally: `uvicorn app.main:app --reload`

Docker build: `docker build -t businesshub-api .`

Docker run: `docker run -p 8000:8000 businesshub-api`

## Docker test command

`docker build -t businesshub-api .` then `docker run -p 8000:8000 businesshub-api` and curl `/health`.

## Git rules

- No direct feature development on `main`. Create a feature branch: `git checkout -b feature/name`.
- Every feature needs tests. Run `python -m pytest -v` before opening a PR.
- Do not commit secrets, API keys, or `.env` files. Configure via GitHub Actions secrets/variables (`RAILWAY_TOKEN`, `RAILWAY_SERVICE`, `APP_URL`) and Railway service variables (`DATABASE_URL`, `OPENROUTER_API_KEY`, optional `OPENROUTER_MODEL`).
- Do not push or deploy unless explicitly requested.
- Do not modify unrelated features in a single PR.
- Verify tests pass after any change.
- Do not create commits or push to GitHub unless instructed.

## CI/CD

CI runs on pull requests to `main`: checkout → Python 3.12 → install dev deps → pytest → docker build. Fails if tests or docker build fail.

Deploy runs on push to `main`: test → write `github.sha` to `app/version.txt` → deploy to Railway → smoke test `$APP_URL/health` verifying `status == "ok"` and `version == $GITHUB_SHA`, with retries.
