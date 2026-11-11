"""BusinessHub API main application entrypoint."""

from fastapi import FastAPI

from app.routers import greet, math, reverse, subtract, wordcount

app = FastAPI(
    title="BusinessHub API",
    description="A small production-style BusinessHub API demonstrating CI/CD workflows.",
    version="dev",
)

# Include feature routers
app.include_router(greet.router)
app.include_router(math.router)
app.include_router(reverse.router)
app.include_router(wordcount.router)
app.include_router(subtract.router)


def _read_version() -> str:
    """Read the application version from version.txt.

    Falls back to 'dev' if the file is missing or unreadable, so the app
    still starts in local development before a Git SHA is written.
    """
    try:
        with open("app/version.txt", "r", encoding="utf-8") as fh:
            version = fh.read().strip()
        if version:
            return version
    except FileNotFoundError:
        pass
    return "dev"


@app.get("/health", tags=["health"])
def health():
    """Health check endpoint.

    Returns the application status and version. The version is loaded from
    app/version.txt so a Git commit SHA can be injected at build/deploy time.
    """
    return {"status": "ok", "version": _read_version()}
