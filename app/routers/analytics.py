from fastapi import APIRouter

router = APIRouter()

@router.get("/summary")
async def get_summary(user: str):
    return {"message": f"Stub analytics for {user}"}
