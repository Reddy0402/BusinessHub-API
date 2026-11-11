"""Reverse router: GET /reverse/{text}."""

from fastapi import APIRouter, Path

router = APIRouter(prefix="/reverse", tags=["reverse"])


@router.get("/{text}")
def reverse_text(text: str = Path(..., description="Text to reverse")):
    """Return the input text reversed."""
    return {"result": text[::-1]}
