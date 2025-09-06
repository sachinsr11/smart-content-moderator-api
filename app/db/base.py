from fastapi import APIRouter

router = APIRouter()

@router.post("/text")
async def moderate_text():
    return {"message": "Stub for text moderation"}

@router.post("/image")
async def moderate_image():
    return {"message": "Stub for image moderation"}
