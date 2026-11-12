from fastapi import APIRouter

router = APIRouter(prefix="/info", tags=["info"])


@router.get("")
def info():
    return {"message": "Team API information"}