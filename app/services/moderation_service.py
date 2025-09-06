import hashlib
from sqlalchemy.orm import Session
from app.models.moderation_request import ModerationRequest, ContentType, RequestStatus
from app.models.moderation_result import ModerationResult
from app.schemas.moderation import ModerationTextRequest, ModerationResultResponse
from app.services.notification_service import send_inappropriate_content_alert
from app.clients.llm_client import classify_text


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def handle_text_moderation(request: ModerationTextRequest, db: Session) -> ModerationResultResponse:
    # 1. Save moderation request
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

    # 2. Call LLM (mocked for now)
    classification, confidence, reasoning, llm_response = classify_text(request.content)

    # 3. Save moderation result
    result = ModerationResult(
        request_id=moderation_request.id,
        classification=classification,
        confidence=confidence,
        reasoning=reasoning,
        llm_response=llm_response,
    )
    db.add(result)

    # 4. Update request status
    moderation_request.status = RequestStatus.completed
    db.commit()
    db.refresh(result)

    # 5. Send notification if flagged
    if classification != "safe":
        send_inappropriate_content_alert(request.email, classification, reasoning)

    # 6. Return response schema
    return ModerationResultResponse(
        request_id=moderation_request.id,
        classification=classification,
        confidence=confidence,
        reasoning=reasoning,
        status=moderation_request.status.value,
        llm_response=llm_response,
    )
