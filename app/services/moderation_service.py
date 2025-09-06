import hashlib
from sqlalchemy.orm import Session
from app.models.moderation_request import ModerationRequest, ContentType, RequestStatus
from app.models.moderation_result import ModerationResult
from app.schemas.moderation import ModerationTextRequest, ModerationImageRequest, ModerationResultResponse
from app.services.notification_service import send_inappropriate_content_alert
from app.clients.llm_client import classify_text, classify_image

def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()

def handle_text_moderation(request: ModerationTextRequest, db: Session) -> ModerationResultResponse:
    content_hash = hash_content(request.content)
    moderation_request = ModerationRequest(
        user_email=request.email,
        content_type=ContentType.text,
        content_hash=content_hash,
        status=RequestStatus.pending,
    )
    db.add(moderation_request)
    db.commit()
    db.refresh(moderation_request)

    classification, confidence, reasoning, llm_response = classify_text(request.content)

    result = ModerationResult(
        request_id=moderation_request.id,
        classification=classification,
        confidence=confidence,
        reasoning=reasoning,
        llm_response=llm_response,
    )
    db.add(result)
    moderation_request.status = RequestStatus.completed
    db.commit()
    db.refresh(result)

    if classification != "safe":
        send_inappropriate_content_alert(
            to_email=request.email,
            classification=classification,
            reasoning=reasoning,
            db=db,
            request_id=moderation_request.id
        )

    return ModerationResultResponse(
        request_id=moderation_request.id,
        classification=classification,
        confidence=confidence,
        reasoning=reasoning,
        status=moderation_request.status.value,
        llm_response=llm_response
    )

def handle_image_moderation(request: ModerationImageRequest, db: Session) -> ModerationResultResponse:
    content_hash = hash_content(request.image_url)
    moderation_request = ModerationRequest(
        user_email=request.email,
        content_type=ContentType.image,
        content_hash=content_hash,
        status=RequestStatus.pending,
    )
    db.add(moderation_request)
    db.commit()
    db.refresh(moderation_request)

    classification, confidence, reasoning, llm_response = classify_image(request.image_url)

    result = ModerationResult(
        request_id=moderation_request.id,
        classification=classification,
        confidence=confidence,
        reasoning=reasoning,
        llm_response=llm_response,
    )
    db.add(result)
    moderation_request.status = RequestStatus.completed
    db.commit()
    db.refresh(result)

    if classification != "safe":
        send_inappropriate_content_alert(
            to_email=request.email,
            classification=classification,
            reasoning=reasoning,
            db=db,
            request_id=moderation_request.id
        )

    return ModerationResultResponse(
        request_id=moderation_request.id,
        classification=classification,
        confidence=confidence,
        reasoning=reasoning,
        status=moderation_request.status.value,
        llm_response=llm_response
    )
