"""
Custom exceptions for the Content Moderator API.

This module defines specific exception types for different error scenarios,
enabling better error handling and more informative error responses.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException


class ContentModeratorException(Exception):
    """Base exception for all content moderator related errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = "CONTENT_MODERATOR_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class LLMServiceException(ContentModeratorException):
    """Exception raised when LLM service fails."""
    
    def __init__(
        self, 
        message: str, 
        provider: str = "unknown",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="LLM_SERVICE_ERROR",
            details={**(details or {}), "provider": provider}
        )


class NotificationServiceException(ContentModeratorException):
    """Exception raised when notification service fails."""
    
    def __init__(
        self, 
        message: str, 
        channel: str = "unknown",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="NOTIFICATION_SERVICE_ERROR",
            details={**(details or {}), "channel": channel}
        )


class DatabaseException(ContentModeratorException):
    """Exception raised when database operations fail."""
    
    def __init__(
        self, 
        message: str, 
        operation: str = "unknown",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details={**(details or {}), "operation": operation}
        )


class ValidationException(ContentModeratorException):
    """Exception raised when input validation fails."""
    
    def __init__(
        self, 
        message: str, 
        field: str = "unknown",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={**(details or {}), "field": field}
        )


class RateLimitException(ContentModeratorException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details={**(details or {}), "retry_after": retry_after}
        )


class ContentTooLargeException(ContentModeratorException):
    """Exception raised when content exceeds size limits."""
    
    def __init__(
        self, 
        message: str = "Content size exceeds limit",
        max_size: int = 0,
        actual_size: int = 0,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="CONTENT_TOO_LARGE",
            details={
                **(details or {}), 
                "max_size": max_size,
                "actual_size": actual_size
            }
        )


def create_http_exception(
    exception: ContentModeratorException,
    status_code: int = 500
) -> HTTPException:
    """
    Convert custom exception to FastAPI HTTPException.
    
    Args:
        exception: Custom exception instance
        status_code: HTTP status code to return
    
    Returns:
        HTTPException instance
    """
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": exception.error_code,
            "message": exception.message,
            "details": exception.details
        }
    )


# Exception to HTTP status code mapping
EXCEPTION_STATUS_MAPPING = {
    LLMServiceException: 503,  # Service Unavailable
    NotificationServiceException: 502,  # Bad Gateway
    DatabaseException: 500,  # Internal Server Error
    ValidationException: 400,  # Bad Request
    RateLimitException: 429,  # Too Many Requests
    ContentTooLargeException: 413,  # Payload Too Large
}
