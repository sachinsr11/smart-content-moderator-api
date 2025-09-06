import hashlib
import asyncio
from typing import Tuple, Dict, Any
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.moderation_request import ModerationRequest, ContentType, RequestStatus
from app.models.moderation_result import ModerationResult
from app.schemas.moderation import (
    ModerationTextRequest,
    ModerationImageRequest,
    ModerationResultResponse,
)
from app.services.notification_service import send_inappropriate_content_alert
from app.clients.llm_client import classify_text, classify_image
from app.core.logger import logger
from app.core.exceptions import (
    DatabaseException,
    ValidationException,
    LLMServiceException,
    create_http_exception
)
from app.core.security import (
    validate_text_content,
    validate_image_url,
    validate_email,
    sanitize_input,
    create_content_hash
)


def hash_content(content: str) -> str:
    """
    Create SHA256 hash of content for deduplication and integrity.
    
    Args:
        content: Content to hash
        
    Returns:
        SHA256 hash as hex string
    """
    return create_content_hash(content)


async def handle_text_moderation(
    request: ModerationTextRequest, 
    db: Session, 
    background_tasks: BackgroundTasks
) -> ModerationResultResponse:
    """
    Handle text content moderation with comprehensive error handling and logging.
    
    Args:
        request: Text moderation request
        db: Database session
        background_tasks: FastAPI background tasks
        
    Returns:
        Moderation result response
        
    Raises:
        ValidationException: If input validation fails
        DatabaseException: If database operations fail
        LLMServiceException: If LLM service fails
    """
    logger.info(
        f"Starting text moderation for user {request.email}",
        extra={
            "user_email": request.email,
            "content_length": len(request.content)
        }
    )
    
    try:
        # Input validation
        if not validate_email(request.email):
            raise ValidationException(
                "Invalid email format",
                field="email"
            )
        
        # Sanitize and validate content
        sanitized_content = sanitize_input(request.content)
        is_valid, error_msg = validate_text_content(sanitized_content)
        if not is_valid:
            raise ValidationException(
                error_msg or "Invalid text content",
                field="content"
            )
        
        # Create content hash for deduplication
        content_hash = hash_content(sanitized_content)
        
        # Check for duplicate requests (optional optimization)
        existing_request = db.query(ModerationRequest).filter(
            ModerationRequest.content_hash == content_hash,
            ModerationRequest.user_email == request.email
        ).first()
        
        if existing_request and existing_request.status == RequestStatus.completed:
            logger.info(
                f"Found duplicate request, returning cached result",
                extra={
                    "user_email": request.email,
                    "existing_request_id": str(existing_request.id)
                }
            )
            # Return cached result
            result = existing_request.results
            return ModerationResultResponse(
                request_id=existing_request.id,
                classification=result.classification,
                confidence=result.confidence,
                reasoning=result.reasoning,
                status=existing_request.status.value,
                llm_response=result.llm_response,
            )
        
        # Create moderation request
        moderation_request = ModerationRequest(
            user_email=request.email,
            content_type=ContentType.text,
            content_hash=content_hash,
            status=RequestStatus.pending,
        )
        
        try:
            db.add(moderation_request)
            db.commit()
            db.refresh(moderation_request)
            
            logger.info(
                f"Created moderation request {moderation_request.id}",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email
                }
            )
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                f"Database error creating moderation request",
                extra={
                    "user_email": request.email,
                    "error": str(e)
                },
                exc_info=True
            )
            raise DatabaseException(
                f"Failed to create moderation request: {str(e)}",
                operation="create_request"
            )
        
        # Classify content using LLM
        try:
            logger.info(
                f"Classifying text content",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email
                }
            )
            
            classification, confidence, reasoning, llm_response = classify_text(sanitized_content)
            
            logger.info(
                f"Text classification completed",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email,
                    "classification": classification,
                    "confidence": confidence
                }
            )
            
        except Exception as e:
            logger.error(
                f"LLM classification failed",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email,
                    "error": str(e)
                },
                exc_info=True
            )
            
            # Update request status to failed
            moderation_request.status = RequestStatus.failed
            db.commit()
            
            raise LLMServiceException(
                f"Text classification failed: {str(e)}",
                provider="llm",
                details={"request_id": str(moderation_request.id)}
            )
        
        # Create moderation result
        try:
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
            
            logger.info(
                f"Moderation result saved successfully",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email,
                    "classification": classification
                }
            )
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                f"Database error saving moderation result",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email,
                    "error": str(e)
                },
                exc_info=True
            )
            raise DatabaseException(
                f"Failed to save moderation result: {str(e)}",
                operation="save_result"
            )
        
        # Schedule notification if content is inappropriate
        if classification != "safe":
            logger.info(
                f"Scheduling notification for inappropriate content",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email,
                    "classification": classification
                }
            )
            
            background_tasks.add_task(
                send_inappropriate_content_alert,
                to_email=request.email,
                classification=classification,
                reasoning=reasoning,
                db=db,
                request_id=moderation_request.id,
            )
        
        return ModerationResultResponse(
            request_id=moderation_request.id,
            classification=classification,
            confidence=confidence,
            reasoning=reasoning,
            status=moderation_request.status.value,
            llm_response=llm_response,
        )
        
    except (ValidationException, DatabaseException, LLMServiceException):
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in text moderation",
            extra={
                "user_email": request.email,
                "error": str(e)
            },
            exc_info=True
        )
        raise DatabaseException(
            f"Unexpected error in text moderation: {str(e)}",
            operation="text_moderation"
        )


async def handle_image_moderation(
    request: ModerationImageRequest, 
    db: Session, 
    background_tasks: BackgroundTasks
) -> ModerationResultResponse:
    """
    Handle image content moderation with comprehensive error handling and logging.
    
    Args:
        request: Image moderation request
        db: Database session
        background_tasks: FastAPI background tasks
        
    Returns:
        Moderation result response
        
    Raises:
        ValidationException: If input validation fails
        DatabaseException: If database operations fail
        LLMServiceException: If LLM service fails
    """
    logger.info(
        f"Starting image moderation for user {request.email}",
        extra={
            "user_email": request.email,
            "image_url": request.image_url[:100] + "..." if len(request.image_url) > 100 else request.image_url
        }
    )
    
    try:
        # Input validation
        if not validate_email(request.email):
            raise ValidationException(
                "Invalid email format",
                field="email"
            )
        
        # Validate image URL
        is_valid, error_msg = validate_image_url(request.image_url)
        if not is_valid:
            raise ValidationException(
                error_msg or "Invalid image URL",
                field="image_url"
            )
        
        # Create content hash for deduplication
        content_hash = hash_content(request.image_url)
        
        # Check for duplicate requests (optional optimization)
        existing_request = db.query(ModerationRequest).filter(
            ModerationRequest.content_hash == content_hash,
            ModerationRequest.user_email == request.email
        ).first()
        
        if existing_request and existing_request.status == RequestStatus.completed:
            logger.info(
                f"Found duplicate image request, returning cached result",
                extra={
                    "user_email": request.email,
                    "existing_request_id": str(existing_request.id)
                }
            )
            # Return cached result
            result = existing_request.results
            return ModerationResultResponse(
                request_id=existing_request.id,
                classification=result.classification,
                confidence=result.confidence,
                reasoning=result.reasoning,
                status=existing_request.status.value,
                llm_response=result.llm_response,
            )
        
        # Create moderation request
        moderation_request = ModerationRequest(
            user_email=request.email,
            content_type=ContentType.image,
            content_hash=content_hash,
            status=RequestStatus.pending,
        )
        
        try:
            db.add(moderation_request)
            db.commit()
            db.refresh(moderation_request)
            
            logger.info(
                f"Created image moderation request {moderation_request.id}",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email
                }
            )
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                f"Database error creating image moderation request",
                extra={
                    "user_email": request.email,
                    "error": str(e)
                },
                exc_info=True
            )
            raise DatabaseException(
                f"Failed to create image moderation request: {str(e)}",
                operation="create_request"
            )
        
        # Classify image using LLM
        try:
            logger.info(
                f"Classifying image content",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email
                }
            )
            
            classification, confidence, reasoning, llm_response = classify_image(request.image_url)
            
            logger.info(
                f"Image classification completed",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email,
                    "classification": classification,
                    "confidence": confidence
                }
            )
            
        except Exception as e:
            logger.error(
                f"LLM image classification failed",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email,
                    "error": str(e)
                },
                exc_info=True
            )
            
            # Update request status to failed
            moderation_request.status = RequestStatus.failed
            db.commit()
            
            raise LLMServiceException(
                f"Image classification failed: {str(e)}",
                provider="llm",
                details={"request_id": str(moderation_request.id)}
            )
        
        # Create moderation result
        try:
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
            
            logger.info(
                f"Image moderation result saved successfully",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email,
                    "classification": classification
                }
            )
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                f"Database error saving image moderation result",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email,
                    "error": str(e)
                },
                exc_info=True
            )
            raise DatabaseException(
                f"Failed to save image moderation result: {str(e)}",
                operation="save_result"
            )
        
        # Schedule notification if content is inappropriate
        if classification != "safe":
            logger.info(
                f"Scheduling notification for inappropriate image content",
                extra={
                    "request_id": str(moderation_request.id),
                    "user_email": request.email,
                    "classification": classification
                }
            )
            
            background_tasks.add_task(
                send_inappropriate_content_alert,
                to_email=request.email,
                classification=classification,
                reasoning=reasoning,
                db=db,
                request_id=moderation_request.id,
            )
        
        return ModerationResultResponse(
            request_id=moderation_request.id,
            classification=classification,
            confidence=confidence,
            reasoning=reasoning,
            status=moderation_request.status.value,
            llm_response=llm_response,
        )
        
    except (ValidationException, DatabaseException, LLMServiceException):
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in image moderation",
            extra={
                "user_email": request.email,
                "error": str(e)
            },
            exc_info=True
        )
        raise DatabaseException(
            f"Unexpected error in image moderation: {str(e)}",
            operation="image_moderation"
        )
