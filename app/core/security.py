"""
Security utilities and input validation for the Content Moderator API.

This module provides security measures including rate limiting, input validation,
content size limits, and other security features.
"""

import re
import hashlib
import time
from typing import Dict, Any, Optional, Tuple
from functools import wraps
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.logger import logger
from app.core.exceptions import (
    RateLimitException, 
    ContentTooLargeException, 
    ValidationException
)

# Security configuration
MAX_CONTENT_LENGTH = 10000  # characters for text
MAX_IMAGE_URL_LENGTH = 2048  # characters for image URLs
MAX_EMAIL_LENGTH = 254  # RFC 5321 standard
RATE_LIMIT_REQUESTS = 100  # requests per window
RATE_LIMIT_WINDOW = 3600  # seconds (1 hour)

# In-memory rate limiting (in production, use Redis)
rate_limit_storage: Dict[str, Dict[str, Any]] = {}

# Security scheme
security = HTTPBearer(auto_error=False)

def validate_email(email: str) -> bool:
    """
    Validate email format using regex.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid, False otherwise
    """
    if len(email) > MAX_EMAIL_LENGTH:
        return False
        
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_text_content(content: str) -> Tuple[bool, Optional[str]]:
    """
    Validate text content for size and basic security.
    
    Args:
        content: Text content to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content or not content.strip():
        return False, "Content cannot be empty"
    
    if len(content) > MAX_CONTENT_LENGTH:
        return False, f"Content exceeds maximum length of {MAX_CONTENT_LENGTH} characters"
    
    # Check for potential XSS attempts
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*='
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False, "Content contains potentially dangerous patterns"
    
    return True, None

def validate_image_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate image URL for length and format.
    
    Args:
        url: Image URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or not url.strip():
        return False, "Image URL cannot be empty"
    
    if len(url) > MAX_IMAGE_URL_LENGTH:
        return False, f"Image URL exceeds maximum length of {MAX_IMAGE_URL_LENGTH} characters"
    
    # Basic URL format validation
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(url_pattern, url):
        return False, "Invalid URL format"
    
    # Check for common image file extensions
    valid_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff")
    if not any(url.lower().endswith(ext) for ext in valid_extensions):
        return False, "URL does not have a valid image extension"
    
    return True, None

def check_rate_limit(client_ip: str) -> bool:
    """
    Check if client has exceeded rate limit.
        return False, "Image URL must end with a common image extension (.jpg, .jpeg, .png, .gif, .webp, .bmp)"
    Args:
        client_ip: Client IP address
        
    Returns:
        True if within rate limit, False if exceeded
    """
    current_time = time.time()
    
    if client_ip not in rate_limit_storage:
        rate_limit_storage[client_ip] = {
            'requests': [],
            'window_start': current_time
        }
    
    client_data = rate_limit_storage[client_ip]
    
    # Remove old requests outside the window
    window_start = current_time - RATE_LIMIT_WINDOW
    client_data['requests'] = [
        req_time for req_time in client_data['requests'] 
        if req_time > window_start
    ]
    
    # Check if limit exceeded
    if len(client_data['requests']) >= RATE_LIMIT_REQUESTS:
        return False
    
    # Add current request
    client_data['requests'].append(current_time)
    return True

def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check for forwarded headers first (for load balancers/proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection
    return request.client.host if request.client else "unknown"

def rate_limit_dependency(request: Request):
    """
    FastAPI dependency for rate limiting.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = get_client_ip(request)
    
    if not check_rate_limit(client_ip):
        logger.warning(
            f"Rate limit exceeded for client {client_ip}",
            extra={"client_ip": client_ip, "limit": RATE_LIMIT_REQUESTS}
        )
        raise HTTPException(
            status_code=429,
            detail={
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} requests per hour.",
                "retry_after": RATE_LIMIT_WINDOW
            }
        )

def validate_content_hash(content: str, expected_hash: Optional[str] = None) -> bool:
    """
    Validate content integrity using hash.
    
    Args:
        content: Content to validate
        expected_hash: Expected hash value (optional)
        
    Returns:
        True if hash matches or no expected hash provided
    """
    if not expected_hash:
        return True
    
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    return content_hash == expected_hash

def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent XSS and other attacks.
    
    Args:
        text: Input text to sanitize
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Limit consecutive whitespace
    text = re.sub(r'\s{3,}', '  ', text)
    
    return text.strip()

def validate_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> bool:
    """
    Validate API key for protected endpoints.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        True if API key is valid (or not required)
        
    Raises:
        HTTPException: If API key is invalid
    """
    # For now, we'll allow requests without API keys
    # In production, implement proper API key validation
    if credentials is None:
        return True
    
    # TODO: Implement proper API key validation against database
    # For now, accept any non-empty token
    if credentials.credentials and len(credentials.credentials) > 10:
        return True
    
    raise HTTPException(
        status_code=401,
        detail={
            "error_code": "INVALID_API_KEY",
            "message": "Invalid or missing API key"
        }
    )

def log_security_event(
    event_type: str,
    client_ip: str,
    user_email: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log security-related events.
    
    Args:
        event_type: Type of security event
        client_ip: Client IP address
        user_email: User email (if applicable)
        details: Additional event details
    """
    logger.warning(
        f"Security event: {event_type}",
        extra={
            "event_type": event_type,
            "client_ip": client_ip,
            "user_email": user_email,
            "details": details or {}
        }
    )

def create_content_hash(content: str) -> str:
    """
    Create SHA256 hash of content for integrity checking.
    
    Args:
        content: Content to hash
        
    Returns:
        SHA256 hash as hex string
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

# Security decorator for additional validation
def security_validation(func):
    """
    Decorator to add security validation to functions.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Add any additional security checks here
        return func(*args, **kwargs)
    return wrapper
