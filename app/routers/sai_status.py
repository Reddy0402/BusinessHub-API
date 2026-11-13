from fastapi import APIRouter

router = APIRouter(prefix="/sai", tags=["sai"])


@router.get("/status")
def sai_status():
    return {"message": "Sai feature is working"}