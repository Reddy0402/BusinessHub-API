"""Wordcount router: POST /wordcount."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="", tags=["wordcount"])


class WordCountRequest(BaseModel):
    """Request body for word counting."""

    text: str = Field(..., description="Text to count words in")


class WordCountResponse(BaseModel):
    """Response body for word counting."""

    count: int = Field(..., description="Number of words in the text")


@router.post("/wordcount", response_model=WordCountResponse)
def wordcount(payload: WordCountRequest):
    """Count the number of whitespace-separated words in the provided text."""
    words = payload.text.split()
    return {"count": len(words)}
