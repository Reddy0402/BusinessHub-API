"""TeamTask API entry point: creates the app, the health check and registers routers."""

from pathlib import Path

from fastapi import FastAPI

from app.routers import tasks

# The deploy pipeline writes the Git commit ID into app/version.txt.
# Locally the file usually does not exist, so the version falls back to "dev".
VERSION_FILE = Path(__file__).parent / "version.txt"


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


# --- Feature routers ---
app.include_router(tasks.router)
# Sai: register the analytics router here, e.g.
#   from app.routers import analytics
#   app.include_router(analytics.router)
