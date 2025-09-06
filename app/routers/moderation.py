from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.moderation import ModerationTextRequest, ModerationResultResponse, ModerationImageRequest
from app.services.moderation_service import handle_text_moderation, handle_image_moderation
from app.core.exceptions import (
    ValidationException,
    DatabaseException,
    LLMServiceException,
    create_http_exception,
    EXCEPTION_STATUS_MAPPING
)
from app.core.security import rate_limit_dependency
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/moderate", tags=["moderation"])

@router.post("/text", response_model=ModerationResultResponse, status_code=200)
async def moderate_text(
    payload: ModerationTextRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_dependency)
):
    """
    Moderate text content for inappropriate material.
    
    This endpoint analyzes text content using AI models and returns classification results.
    If inappropriate content is detected, notifications are sent via email and Slack.
    
    Args:
        payload: Text moderation request containing email and content
        background_tasks: FastAPI background tasks for notifications
        request: FastAPI request object for logging
        db: Database session
        _: Rate limiting dependency
        
    Returns:
        ModerationResultResponse: Classification results and metadata
        
    Raises:
        HTTPException: Various error conditions with appropriate status codes
    """
    logger.info(
        f"Text moderation request received",
        extra={
            "user_email": payload.email,
            "content_length": len(payload.content),
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    try:
        result = await handle_text_moderation(payload, db, background_tasks)
        
        logger.info(
            f"Text moderation completed successfully",
            extra={
                "request_id": str(result.request_id),
                "user_email": payload.email,
                "classification": result.classification
            }
        )
        
        return result
        
    except ValidationException as e:
        logger.warning(
            f"Text moderation validation failed",
            extra={
                "user_email": payload.email,
                "error": str(e),
                "field": e.details.get("field", "unknown")
            }
        )
        raise create_http_exception(e, 400)
        
    except DatabaseException as e:
        logger.error(
            f"Text moderation database error",
            extra={
                "user_email": payload.email,
                "error": str(e),
                "operation": e.details.get("operation", "unknown")
            },
            exc_info=True
        )
        raise create_http_exception(e, 500)
        
    except LLMServiceException as e:
        logger.error(
            f"Text moderation LLM service error",
            extra={
                "user_email": payload.email,
                "error": str(e),
                "provider": e.details.get("provider", "unknown")
            },
            exc_info=True
        )
        raise create_http_exception(e, 503)
        
    except Exception as e:
        logger.error(
            f"Unexpected error in text moderation",
            extra={
                "user_email": payload.email,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during text moderation",
                "details": {"error": str(e)}
            }
        )

@router.post("/image", response_model=ModerationResultResponse, status_code=200)
async def moderate_image(
    payload: ModerationImageRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_dependency)
):
    """
    Moderate image content for inappropriate material.
    
    This endpoint analyzes image content using AI vision models and returns classification results.
    If inappropriate content is detected, notifications are sent via email and Slack.
    
    Args:
        payload: Image moderation request containing email and image URL
        background_tasks: FastAPI background tasks for notifications
        request: FastAPI request object for logging
        db: Database session
        _: Rate limiting dependency
        
    Returns:
        ModerationResultResponse: Classification results and metadata
        
    Raises:
        HTTPException: Various error conditions with appropriate status codes
    """
    logger.info(
        f"Image moderation request received",
        extra={
            "user_email": payload.email,
            "image_url_length": len(payload.image_url),
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    try:
        result = await handle_image_moderation(payload, db, background_tasks)
        
        logger.info(
            f"Image moderation completed successfully",
            extra={
                "request_id": str(result.request_id),
                "user_email": payload.email,
                "classification": result.classification
            }
        )
        
        return result
        
    except ValidationException as e:
        logger.warning(
            f"Image moderation validation failed",
            extra={
                "user_email": payload.email,
                "error": str(e),
                "field": e.details.get("field", "unknown")
            }
        )
        raise create_http_exception(e, 400)
        
    except DatabaseException as e:
        logger.error(
            f"Image moderation database error",
            extra={
                "user_email": payload.email,
                "error": str(e),
                "operation": e.details.get("operation", "unknown")
            },
            exc_info=True
        )
        raise create_http_exception(e, 500)
        
    except LLMServiceException as e:
        logger.error(
            f"Image moderation LLM service error",
            extra={
                "user_email": payload.email,
                "error": str(e),
                "provider": e.details.get("provider", "unknown")
            },
            exc_info=True
        )
        raise create_http_exception(e, 503)
        
    except Exception as e:
        logger.error(
            f"Unexpected error in image moderation",
            extra={
                "user_email": payload.email,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during image moderation",
                "details": {"error": str(e)}
            }
        )
