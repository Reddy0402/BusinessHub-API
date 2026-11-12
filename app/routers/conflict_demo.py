from fastapi import APIRouter

router = APIRouter(prefix="/conflict-demo", tags=["conflict-demo"])


@router.get("")
def conflict_demo():
    return {"message": "Conflict demo endpoint"}