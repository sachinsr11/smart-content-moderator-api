from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.moderation import ModerationTextRequest, ModerationResultResponse, ModerationImageRequest
from app.services.moderation_service import handle_text_moderation, handle_image_moderation

router = APIRouter(prefix="/api/v1/moderate", tags=["moderation"])

@router.post("/text", response_model=ModerationResultResponse)
def moderate_text(
    payload: ModerationTextRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    return handle_text_moderation(payload, db, background_tasks)

@router.post("/image", response_model=ModerationResultResponse)
def moderate_image(
    payload: ModerationImageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    return handle_image_moderation(payload, db, background_tasks)
