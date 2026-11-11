from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/add", tags=["math"])


class AddResponse(BaseModel):
    result: float


@router.get("", response_model=AddResponse)
def add_numbers(
    a: float = Query(..., description="First number"),
    b: float = Query(..., description="Second number"),
):
    return {"result": a + b}
