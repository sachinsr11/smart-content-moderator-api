from fastapi import APIRouter
from app.db.session import Base
from app.models.moderation_request import ModerationRequest
from app.models.moderation_result import ModerationResult
from app.models.notification_log import NotificationLog


router = APIRouter()

@router.post("/text")
async def moderate_text():
    return {"message": "Stub for text moderation"}

@router.post("/image")
async def moderate_image():
    return {"message": "Stub for image moderation"}
