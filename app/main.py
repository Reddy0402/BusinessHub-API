"""TeamTask API entry point: creates the app, the health check and registers routers."""

from pathlib import Path

from dotenv import load_dotenv

# Local development: read DATABASE_URL / OPENROUTER_API_KEY from a git-ignored .env file.
# Must run before app.db is imported. Variables that are already set are not overridden.
load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from app.routers import jani_message
from app.routers import ai  # noqa: E402
from app.routers import analytics  # noqa: E402
from app.routers import conflict_demo  # noqa: E402
from app.routers import info  # noqa: E402
from app.routers import tasks  # noqa: E402



# The deploy pipeline writes the Git commit ID into app/version.txt.
# Locally the file usually does not exist, so the version falls back to "dev".
VERSION_FILE = Path(__file__).parent / "version.txt"
WEB_UI_FILE = Path(__file__).parent / "static" / "index.html"


def read_version() -> str:
    """Return the contents of version.txt, or "dev" if it is missing or empty."""
    try:
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "dev"
    return version or "dev"


app = FastAPI(
    title="TeamTask API",
    description="Smart task tracker: task management, productivity analytics and an AI assistant.",
)


@app.get("/health", tags=["health"])
def health():
    """Liveness check. Does not touch the database or the AI, so it works on its own."""
    return {"status": "ok", "version": read_version()}


@app.get("/", include_in_schema=False)
def web_ui():
    """The browser app: a single HTML page that calls the API below."""
    return FileResponse(WEB_UI_FILE)


# --- Feature routers ---
app.include_router(tasks.router)
app.include_router(analytics.router)
app.include_router(conflict_demo.router)
app.include_router(info.router)
app.include_router(ai.router)
app.include_router(jani_message.router)