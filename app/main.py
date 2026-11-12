"""TeamTask API entry point: creates the app, the health check and registers routers."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from app.routers import analytics
from app.routers import conflict_demo
from app.routers import info
from app.routers import tasks


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
    description="Smart task tracker: task management plus productivity analytics.",
)


@app.get("/health", tags=["health"])
def health():
    """Liveness check. Does not touch the task store, so it works on its own."""
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