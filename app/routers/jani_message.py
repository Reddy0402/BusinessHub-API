from fastapi import APIRouter

router = APIRouter(prefix="/jani", tags=["jani"])


@router.get("/message")
def jani_message():
    return {"message": "Jani feature is working"}