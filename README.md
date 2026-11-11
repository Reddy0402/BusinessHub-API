# BusinessHub API

A small, production-style FastAPI API demonstrating a complete CI/CD workflow:
developer branch → pull request → GitHub Actions CI → code review → merge to main → GitHub Actions → Docker build → Railway deployment → production smoke test.

## Architecture

```
BusinessHub-API/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, health endpoint, router registration
│   ├── version.txt      # Application version (dev locally, Git SHA in prod)
│   └── routers/
│       ├── __init__.py
│       ├── greet.py     # GET /greet/{name}
│       ├── math.py      # GET /add?a=&b=
│       ├── reverse.py   # GET /reverse/{text}
│       └── wordcount.py # POST /wordcount
├── tests/
│   ├── test_health.py
│   ├── test_greet.py
│   ├── test_math.py
│   ├── test_reverse.py
│   └── test_wordcount.py
├── requirements.txt     # Production dependencies
├── requirements-dev.txt # Test and development dependencies
├── Dockerfile
├── .dockerignore
├── .gitignore
├── AGENTS.md            # Agent instructions
└── .github/
    └── workflows/
        ├── ci.yml       # Runs on pull requests to main
        └── deploy.yml   # Runs on push to main (test → deploy → smoke-test)
```

Each feature lives in its own router module under `app/routers/` and is registered in `app/main.py`. No business logic lives directly in `main.py`.

## API Endpoints

### GET /health
Health check. Returns status and version (loaded from `app/version.txt`).

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"dev"}
```

### GET /greet/{name}
Returns a personalized greeting.

```bash
curl http://localhost:8000/greet/Sai
# {"message":"Hello, Sai!"}
```

### GET /add?a=2&b=3
Adds two integers.

```bash
curl "http://localhost:8000/add?a=2&b=3"
# {"result":5}
```

### GET /reverse/{text}
Reverses the input text.

```bash
curl http://localhost:8000/reverse/hello
# {"result":"olleh"}
```

### POST /wordcount
Counts whitespace-separated words in the provided text.

```bash
curl -X POST http://localhost:8000/wordcount \
  -H "Content-Type: application/json" \
  -d '{"text":"hello world from BusinessHub"}'
# {"count":4}
```

## Local Python Setup

Python 3.12 is required.

### Virtual environment

Create and activate a virtual environment:

```bash
# Create
python -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
source .venv/bin/activate
```

### Installing dependencies

Production dependencies:

```bash
pip install -r requirements.txt
```

Development/test dependencies (includes production):

```bash
pip install -r requirements-dev.txt
```

### Running tests

```bash
python -m pytest -v
```

Run a single test file:

```bash
python -m pytest tests/test_health.py -v
```

### Running FastAPI locally

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Open `http://localhost:8000/docs` for the interactive Swagger UI.

## Docker

### Build

```bash
docker build -t businesshub-api .
```

### Run

```bash
docker run -p 8000:8000 businesshub-api
```

Or with a custom port:

```bash
docker run -p 9000:9000 -e PORT=9000 businesshub-api
```

Verify the container:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/greet/Sai
```

## Git Branch Strategy

- `main` is the production branch. No direct feature development on `main`.
- Create a feature branch for every feature or bug fix: `git checkout -b feature/feature-name`.
- Open a pull request from the feature branch to `main`.
- GitHub Actions CI runs on every pull request targeting `main`.
- Squash and merge into `main` after review.
- The deploy workflow triggers on push to `main`.

## Pull Request Workflow

1. Create a branch from `main`.
2. Implement the feature with tests.
3. Run `python -m pytest -v` locally — all tests must pass.
4. Open a pull request targeting `main`.
5. GitHub Actions CI runs (pytest + Docker build). It must pass.
6. Code review.
7. Merge to `main` (squash merge).
8. The deploy workflow runs automatically: test → deploy to Railway → smoke test.

## GitHub Actions CI

`.github/workflows/ci.yml` runs on pull requests targeting `main`:

1. Checkout repository
2. Set up Python 3.12
3. Install development dependencies (`requirements-dev.txt`)
4. Run `python -m pytest -v`
5. Build the Docker image

The job fails if tests fail or the Docker build fails.

## Railway Deployment

Deployment is controlled by GitHub Actions, not by connecting Railway directly to GitHub (to avoid duplicate deployments).

### Secrets / Variables

Configure these in your GitHub repository settings (Settings → Secrets and variables → Actions):

| Name | Type | Description |
|------|------|-------------|
| `RAILWAY_TOKEN` | Secret | Railway authentication token |
| `RAILWAY_SERVICE` | Variable | Railway service name/ID |
| `APP_URL` | Variable | Public URL of the deployed Railway service |

Do not commit secrets or `.env` files to the repository.

### Deploy workflow

`.github/workflows/deploy.yml` runs on push to `main`:

1. **test** — runs pytest
2. **deploy** — writes the GitHub commit SHA into `app/version.txt`, then deploys to Railway
3. **smoke-test** — calls `$APP_URL/health`, retries for up to 5 minutes, verifies `status == "ok"` and `version == $GITHUB_SHA`

## Smoke Testing

After deployment, the smoke test calls `$APP_URL/health` and verifies:

- `status == "ok"`
- `version == $GITHUB_SHA` (the exact GitHub commit SHA)

The smoke test retries every 10 seconds for up to 30 attempts (5 minutes) because deployment may take time to become available. If the version does not match the commit SHA, the workflow fails.

## Team Development Workflow

1. Never push directly to `main`.
2. Every feature must include tests.
3. Run `python -m pytest -v` before opening a pull request.
4. Do not commit secrets, API keys, or `.env` files.
5. Do not push or deploy unless explicitly requested.
6. Do not modify unrelated features in a single pull request.
7. Verify tests pass after any change.
