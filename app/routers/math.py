"""Math router: GET /add?a=2&b=3."""

from fastapi import APIRouter, Query

router = APIRouter(prefix="", tags=["math"])


@router.get("/add")
def add(
    a: int = Query(..., description="First integer operand"),
    b: int = Query(..., description="Second integer operand"),
):
    """Add two integers and return the result."""
    return {"result": a + b}
