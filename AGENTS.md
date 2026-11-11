# BusinessHub API — Agent Instructions

Python 3.12 FastAPI service. Small production-style API demonstrating CI/CD:
branch → PR → GitHub Actions CI → merge to main → deploy → smoke test.

## Project architecture

- `app/main.py` — FastAPI app (title: "BusinessHub API"), `/health` endpoint, router registration. No business logic here.
- `app/version.txt` — version string ("dev" locally, Git commit SHA in production). `/health` reads it at runtime.
- `app/routers/greet.py` — `GET /greet/{name}`
- `app/routers/math.py` — `GET /add?a=&b=`
- `app/routers/reverse.py` — `GET /reverse/{text}`
- `app/routers/wordcount.py` — `POST /wordcount` (Pydantic request/response models)
- `tests/` — pytest tests, one file per router plus test_health.py
- `requirements.txt` — production deps (fastapi, uvicorn)
- `requirements-dev.txt` — adds pytest, httpx
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
- Do not commit secrets, API keys, or `.env` files. Configure via GitHub Actions secrets/variables (`RAILWAY_TOKEN`, `RAILWAY_SERVICE`, `APP_URL`).
- Do not push or deploy unless explicitly requested.
- Do not modify unrelated features in a single PR.
- Verify tests pass after any change.
- Do not create commits or push to GitHub unless instructed.

## CI/CD

CI runs on pull requests to `main`: checkout → Python 3.12 → install dev deps → pytest → docker build. Fails if tests or docker build fail.

Deploy runs on push to `main`: test → write `github.sha` to `app/version.txt` → deploy to Railway → smoke test `$APP_URL/health` verifying `status == "ok"` and `version == $GITHUB_SHA`, with retries.
