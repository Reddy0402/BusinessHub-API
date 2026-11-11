"""Greet router: GET /greet/{name}."""

from fastapi import APIRouter, Path

router = APIRouter(prefix="/greet", tags=["greet"])


@router.get("/{name}")
def greet_name(name: str = Path(..., description="Name to greet", min_length=1)):
    """Return a personalized greeting for the given name."""
    return {"message": f"Hello, {name}!"}
