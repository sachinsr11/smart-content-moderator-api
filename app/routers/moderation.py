from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.moderation import ModerationTextRequest, ModerationImageRequest, ModerationResultResponse
from app.services.moderation_service import handle_text_moderation, handle_image_moderation

router = APIRouter()

@router.post("/text", response_model=ModerationResultResponse)
async def moderate_text(payload: ModerationTextRequest, db: Session = Depends(get_db)):
    return handle_text_moderation(payload, db)


@router.post("/image", response_model=ModerationResultResponse)
async def moderate_image(payload: ModerationImageRequest, db: Session = Depends(get_db)):
    return handle_image_moderation(payload, db)
