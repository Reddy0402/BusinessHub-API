"""Subtract router: GET /subtract?a=5&b=3."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/subtract", tags=["math"])


class SubtractResponse(BaseModel):
    result: float


@router.get("", response_model=SubtractResponse)
def subtract_numbers(
    a: float = Query(..., description="Number to subtract from"),
    b: float = Query(..., description="Number to subtract"),
):
    """Return a minus b."""
    return {"result": a - b}
