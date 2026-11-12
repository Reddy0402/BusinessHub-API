# TeamTask API

A production-style FastAPI task management application built as a CI/CD workshop project using **FastAPI, Docker, GitHub Actions, GitHub Pull Requests, and Railway**.

The project demonstrates a complete development workflow:

**Feature Branch → Pull Request → Code Review → Automated Tests → Docker Build → Merge → Railway Deployment → Smoke Test**

---

## 🚀 Features

### Task Management

The API provides complete task management functionality:

- Create tasks
- List tasks
- Retrieve a task
- Update tasks
- Delete tasks
- Task priority management
- Task status management
- Due-date tracking
- Validation of request data

### Productivity Analytics

The analytics module provides:

- Total task count
- Completed task count
- Pending task count
- Overdue task count
- Completion percentage
- Task breakdown by priority

### Browser Web UI

The project also includes a lightweight browser interface for interacting with the API.

The web application supports:

- Creating tasks
- Searching tasks
- Filtering tasks
- Editing tasks
- Completing tasks
- Deleting tasks
- Viewing productivity analytics

The UI is implemented as a single HTML page and does not require a separate frontend build system.

---

## 🏗️ Architecture

```text
                         ┌─────────────────────┐
                         │      Developer      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   Feature Branch    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Pull Request     │
                         └──────────┬──────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                  Code Review             GitHub Actions
                                              │
                                      ┌───────┴────────┐
                                      │                │
                                    Tests          Docker Build
                                      │                │
                                      └───────┬────────┘
                                              ▼
                                    ┌──────────────────┐
                                    │ Protected main   │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │ GitHub Actions CD │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │     Railway      │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │ /health Smoke    │
                                    │      Test        │
                                    └──────────────────┘
```

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming language |
| FastAPI | REST API framework |
| Uvicorn | ASGI application server |
| Pytest | Automated testing |
| Docker | Containerization |
| Git | Version control |
| GitHub | Source code and pull requests |
| GitHub Actions | CI/CD automation |
| Railway | Cloud deployment |
| HTML/CSS/JavaScript | Browser UI |

---

## 📁 Project Structure

```text
BusinessHub-API/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── store.py
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── tasks.py
│   │   ├── analytics.py
│   │   ├── conflict_demo.py
│   │   └── info.py
│   │
│   └── static/
│       └── index.html
│
├── tests/
│   ├── test_health.py
│   ├── test_analytics.py
│   └── test_web_ui.py
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
├── docs/
│   └── CONFLICT-RESOLUTION.md
│
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── .dockerignore
├── .gitignore
├── README.md
└── LICENSE
```

---

# 📋 Task Model

Each task contains the following fields:

| Field | Type | Rules |
|---|---|---|
| `id` | integer | Set by the server |
| `title` | string | Required, 1–200 characters |
| `description` | string or null | Optional, up to 1000 characters |
| `priority` | `low` / `medium` / `high` | Defaults to `medium` |
| `status` | `pending` / `completed` | Defaults to `pending` |
| `due_date` | date or null | Optional, `YYYY-MM-DD` |

Unknown fields are rejected with HTTP `422`.

---

# 🔌 API Endpoints

## Health

### `GET /health`

Returns the current application health and deployed version.

Example:

```json
{
  "status": "ok",
  "version": "7af50143d1538f5de8573a8143162c6493767c2f"
}
```

The `version` is populated from `app/version.txt`.

During deployment, GitHub Actions writes the current Git commit SHA into this file. This allows the deployment smoke test to verify that Railway is running the exact commit that was deployed.

---

## Tasks

### `POST /tasks`

Create a new task.

Returns:

```text
201 Created
```

---

### `GET /tasks`

Returns the list of tasks.

Returns:

```text
200 OK
```

---

### `GET /tasks/{task_id}`

Retrieve a specific task.

Possible responses:

```text
200 OK
404 Not Found
```

---

### `PUT /tasks/{task_id}`

Update an existing task.

Only the fields that need to change have to be provided.

Possible responses:

```text
200 OK
404 Not Found
422 Validation Error
```

---

### `DELETE /tasks/{task_id}`

Delete a task.

Returns:

```text
204 No Content
```

If the task does not exist:

```text
404 Not Found
```

---

# 📊 Analytics

### `GET /analytics`

Returns productivity analytics for the current task collection.

The analytics include:

- Total tasks
- Completed tasks
- Pending tasks
- Overdue tasks
- Completion percentage
- Priority distribution

Example response:

```json
{
  "total_tasks": 10,
  "completed_tasks": 6,
  "pending_tasks": 4,
  "overdue_tasks": 2,
  "completion_percentage": 60.0
}
```

---

# 🧪 Demo Endpoints

The repository also contains endpoints created as part of the GitHub branching and merge-conflict exercise.

### `GET /conflict-demo`

Returns:

```json
{
  "message": "Conflict demo endpoint"
}
```

### `GET /info`

Returns:

```json
{
  "message": "Team API information"
}
```

These endpoints demonstrate how multiple developers can independently add features and later resolve conflicts when integrating their changes.

---

# 🌐 Web Application

The browser UI is available at:

```text
http://localhost:8000/
```

It is implemented as:

```text
app/static/index.html
```

The frontend communicates directly with the FastAPI backend.

No separate frontend build step is required.

---

# 📖 Interactive API Documentation

FastAPI automatically provides interactive API documentation.

Once the application is running:

```text
http://localhost:8000/docs
```

Alternative documentation:

```text
http://localhost:8000/redoc
```

---

# 💻 Running Locally

## 1. Clone the repository

```bash
git clone https://github.com/Reddy0402/BusinessHub-API.git
cd BusinessHub-API
```

---

## 2. Create a virtual environment

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

### Windows CMD

```cmd
py -3.12 -m venv .venv
.venv\Scripts\activate
```

---

## 3. Install development dependencies

```bash
pip install -r requirements-dev.txt
```

---

## 4. Run the tests

```bash
python -m pytest -v
```

The project currently contains **13 automated tests** covering:

- Health endpoint
- Version handling
- Analytics calculations
- Edge cases
- Browser UI
- API behavior

Expected result:

```text
13 passed
```

---

## 5. Start the application

```bash
uvicorn app.main:app --reload
```

The application will be available at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

Web UI:

```text
http://localhost:8000/
```

---

# 🐳 Docker

The application can be packaged and executed as a single Docker container.

## Build the image

```bash
docker build -t team-api .
```

## Run the container

```bash
docker run --rm -p 8000:8000 team-api
```

The container listens on:

```text
0.0.0.0
```

and uses the `PORT` environment variable.

The default port is:

```text
8000
```

---

# 🔄 GitHub Workflow

The project follows a pull-request-based development workflow.

The `main` branch is protected.

Changes follow this process:

```text
Feature Branch
      ↓
Pull Request
      ↓
Code Review
      ↓
GitHub Actions CI
      ↓
Required Approval
      ↓
Merge to main
      ↓
Automatic Deployment
```

Direct changes to `main` are not used for normal development.

---

# 🔐 Branch Protection

The `main` branch is protected with the following requirements:

- Changes must be submitted through a Pull Request
- At least one approval is required
- Required CI status check must pass
- Force pushes are blocked
- Pull requests must satisfy the repository rules before merging

This ensures that untested changes cannot directly enter production.

---

# ⚙️ Continuous Integration

GitHub Actions automatically runs CI for Pull Requests.

The CI process includes:

1. Checkout repository
2. Install Python
3. Install development dependencies
4. Run automated tests
5. Build the Docker image

A Pull Request cannot be merged when the required CI checks fail.

---

# 🚀 Continuous Deployment

After a Pull Request is merged into `main`, GitHub Actions starts the deployment pipeline.

The deployment process is:

```text
Push/Merge to main
        ↓
Run tests
        ↓
Build application
        ↓
Write Git commit SHA
        ↓
Deploy to Railway
        ↓
Run smoke test
        ↓
Verify /health
```

The deployment pipeline writes the GitHub commit SHA into:

```text
app/version.txt
```

Railway then serves this value through:

```text
GET /health
```

This makes it possible to verify that the deployed application corresponds to the expected Git commit.

---

# ☁️ Railway Deployment

The production application is deployed on Railway.

Production health endpoint:

```text
https://businesshub-api-production.up.railway.app/health
```

A successful response looks like:

```json
{
  "status": "ok",
  "version": "7af50143d1538f5de8573a8143162c6493767c2f"
}
```

The `version` should match the Git commit SHA deployed by GitHub Actions.

---

# 🧪 Deployment Smoke Test

The deployment pipeline automatically checks the production application after deployment.

The smoke test verifies:

1. The Railway application is reachable.
2. `/health` returns HTTP `200`.
3. `status` is `ok`.
4. The deployed `version` matches the GitHub commit SHA.

This prevents a deployment from being considered successful merely because the container started.

---

# 🔀 Merge Conflict Exercise

This repository also demonstrates how merge conflicts are handled in a collaborative development environment.

Two feature branches independently modified `app/main.py`:

```text
feature/conflict-demo
feature/conflict-demo-other
```

The changes overlapped in the router registration section of `app/main.py`.

When the second feature branch was updated with `main`, Git reported a merge conflict.

The conflict was resolved by keeping both router implementations:

```text
/conflict-demo
/info
```

The resolved changes were tested successfully:

```text
13 passed
```

The conflict-resolution work is documented in:

```text
docs/CONFLICT-RESOLUTION.md
```

The relevant Git history includes:

```text
7c69057  Add conflict demo endpoint
a365544  Add info endpoint for conflict demo
fd240fd  Resolve merge conflict with main
7af5014  Merge pull request #13
```

---

# ❌ CI Failure Exercise

The project also includes a deliberate CI failure exercise.

A test assertion was intentionally changed to an incorrect expected value.

GitHub Actions correctly detected the failure and prevented the Pull Request from being merged.

The test was then corrected and CI returned to a passing state.

This demonstrates that the protected `main` branch relies on automated verification rather than manual checking alone.

---

# 🧑‍💻 Development Workflow

For a new feature:

```bash
git switch main
git pull origin main

git switch -c feature/my-feature
```

Implement the feature and tests.

Run:

```bash
python -m pytest -v
```

Then:

```bash
git add .
git commit -m "Add my feature"
git push -u origin feature/my-feature
```

Open a Pull Request targeting:

```text
main
```

After review and successful CI, merge the Pull Request.

---

# 🧹 Code Quality

Before submitting a Pull Request, run:

```bash
python -m pytest -v
```

and:

```bash
git diff --check
```

The first verifies the automated test suite.

The second checks for common whitespace and patch formatting problems.

---

# 🗄️ Data Storage

The application intentionally uses an **in-memory task store**.

There is no external database.

Therefore:

> Task data is reset whenever the application/container restarts.

This keeps the project simple and focused on API development and CI/CD rather than database infrastructure.

---

# 🔒 Security Notes

Secrets such as Railway authentication tokens must not be committed to Git.

Sensitive configuration should be provided through environment variables or GitHub Actions secrets.

For example:

```text
RAILWAY_TOKEN
```

should be stored as a GitHub Actions secret rather than inside the repository.

---

# 📜 License

This project is licensed under the **Apache License 2.0**.

See:

```text
LICENSE
```

for the complete license text.

---

# 👥 Contributors

| Contributor | Area |
|---|---|
| Sai | Productivity analytics, CI/CD and related features |
| Jaanageswar | Task management |

The project was developed collaboratively using GitHub Pull Requests, code review, protected branches, automated CI, and Railway deployment.

---

# ✅ Project Status

The project demonstrates a complete CI/CD workflow:

- ✅ FastAPI REST API
- ✅ Task management
- ✅ Productivity analytics
- ✅ Browser UI
- ✅ Automated tests
- ✅ Docker containerization
- ✅ GitHub Pull Request workflow
- ✅ Branch protection
- ✅ Code review
- ✅ Merge conflict resolution
- ✅ Deliberate CI failure and recovery
- ✅ GitHub Actions CI
- ✅ Railway deployment
- ✅ Deployment smoke testing
- ✅ Commit SHA verification
