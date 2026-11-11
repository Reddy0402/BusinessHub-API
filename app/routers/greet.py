"""Greet router: GET /greet/{name}."""

from fastapi import APIRouter, Path
from pydantic import BaseModel

router = APIRouter(prefix="/greet", tags=["greet"])


class GreetResponse(BaseModel):
    """Response body for the greet endpoint."""

    message: str


@router.get("/{name}", response_model=GreetResponse)
def greet_name(
    name: str = Path(
        ...,
        description="Name to greet",
        min_length=1,
        max_length=100,
    ),
):
    """Return a personalized greeting for the given name."""
    return {"message": f"Hello, {name}!"}
