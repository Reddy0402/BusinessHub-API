# TeamTask API

A small task tracker REST API built with **FastAPI** for a CI/CD workshop (Docker, GitHub Actions, Railway).

| Feature | Owner | Code |
|---|---|---|
| Task management (create, list, get, update, delete) | Jaanageswar | `app/routers/tasks.py` |
| Productivity analytics (counts, overdue, completion %, by priority) | Sai | `app/routers/analytics.py` (to be built on Sai's feature branch) |

Both features share one in-memory store: `app/store.py`. There is no database on purpose, so data resets when the app restarts.

## Task model

| Field | Type | Rules |
|---|---|---|
| `id` | integer | set by the server |
| `title` | string | required, 1–200 characters, spaces trimmed |
| `description` | string or null | optional, up to 1000 characters |
| `priority` | `low` / `medium` / `high` | default `medium` |
| `status` | `pending` / `completed` | default `pending` |
| `due_date` | date (`YYYY-MM-DD`) or null | optional; past dates allowed so overdue tasks can exist |

Unknown fields are rejected with `422`.

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | `/health` | `200` `{"status": "ok", "version": "..."}` | |
| POST | `/tasks` | `201` the created task | `422` invalid body |
| GET | `/tasks` | `200` list of tasks | |
| GET | `/tasks/{task_id}` | `200` the task | `404` not found |
| PUT | `/tasks/{task_id}` | `200` the updated task (send only the fields to change) | `404`, `422` |
| DELETE | `/tasks/{task_id}` | `204` no body | `404` |

**Web app:** `http://localhost:8000/` is a browser UI for creating, searching, filtering, editing, completing and deleting tasks. It's a single page (`app/static/index.html`) that calls the API above, with no extra packages and no build step.

Interactive API docs: `http://localhost:8000/docs`

`/health` reads its version from `app/version.txt`. The deploy pipeline writes the commit ID there. Locally the file doesn't exist, so it shows `dev`. Don't commit `app/version.txt`, and don't add it to `.gitignore` either, because the Railway CLI skips ignored files when uploading.

## Run locally (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest -v
uvicorn app.main:app --reload
```

Always run the tests from the repository root, or Python won't find the `app` package.

## Docker

```powershell
docker build -t team-api .
docker run --rm -p 8000:8000 team-api
```

The container listens on `0.0.0.0` and on the `PORT` environment variable (default `8000`), which is how Railway routes traffic.

## Workflow

`main` only changes through pull requests: branch → PR → CI + review by the other developer → merge → deploy. The CI and deploy workflows are added during the workshop.
