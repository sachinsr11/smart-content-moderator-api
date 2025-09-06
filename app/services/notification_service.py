import os
import requests
import json
import time
from typing import Optional
from app.db.session import get_db
from app.models.notification_log import NotificationLog
from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import NotificationServiceException, create_http_exception
from sqlalchemy.orm import Session

# Configuration for retry logic
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
TIMEOUT = 30  # seconds

def send_email_notification(
    to_email: str, 
    classification: str, 
    reasoning: str, 
    db: Session, 
    request_id
) -> bool:
    """
    Send email notification via Brevo API with retry logic and proper error handling.
    
    Args:
        to_email: Recipient email address
        classification: Content classification result
        reasoning: AI reasoning for classification
        db: Database session
        request_id: Request ID for logging
    
    Returns:
        True if email sent successfully, False otherwise
        
    Raises:
        NotificationServiceException: If email sending fails after retries
    """
    logger.info(
        f"Attempting to send email notification",
        extra={
            "request_id": request_id,
            "user_email": to_email,
            "classification": classification,
            "channel": "email"
        }
    )
    
    try:
        if not settings.brevo_api_key:
            logger.warning(
                "Brevo API key not configured, using mock email",
                extra={"request_id": request_id, "user_email": to_email}
            )
            return _log_mock_notification(db, request_id, "email", "sent")
            
        # Brevo API integration with retry logic
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": settings.brevo_api_key,
            "content-type": "application/json"
        }
        
        data = {
            "sender": {"name": "Content Moderator", "email": "noreply@moderator.com"},
            "to": [{"email": to_email}],
            "subject": f"Content Moderation Alert - {classification.title()}",
            "htmlContent": f"""
            <h2>Content Moderation Alert</h2>
            <p>Your submitted content has been flagged as <strong>{classification}</strong>.</p>
            <p><strong>Reasoning:</strong> {reasoning}</p>
            <p>Please review our content guidelines and resubmit appropriate content.</p>
            <hr>
            <p><small>This is an automated message from the Content Moderation System.</small></p>
            """
        }
        
        # Retry logic for API calls
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=data, 
                    timeout=TIMEOUT
                )
                
                if response.status_code == 201:
                    logger.info(
                        "Email notification sent successfully",
                        extra={
                            "request_id": request_id,
                            "user_email": to_email,
                            "attempt": attempt + 1
                        }
                    )
                    _log_notification_attempt(db, request_id, "email", "sent")
                    return True
                else:
                    logger.warning(
                        f"Email API returned status {response.status_code}",
                        extra={
                            "request_id": request_id,
                            "status_code": response.status_code,
                            "attempt": attempt + 1,
                            "response": response.text[:200]
                        }
                    )
                    
            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Email API request failed on attempt {attempt + 1}",
                    extra={
                        "request_id": request_id,
                        "error": str(e),
                        "attempt": attempt + 1
                    }
                )
                
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                else:
                    raise NotificationServiceException(
                        f"Email notification failed after {MAX_RETRIES} attempts: {str(e)}",
                        channel="email",
                        details={"attempts": MAX_RETRIES, "error": str(e)}
                    )
        
        # If we get here, all retries failed
        _log_notification_attempt(db, request_id, "email", "failed")
        return False
        
    except NotificationServiceException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in email notification",
            extra={
                "request_id": request_id,
                "user_email": to_email,
                "error": str(e)
            },
            exc_info=True
        )
        _log_notification_attempt(db, request_id, "email", "failed")
        raise NotificationServiceException(
            f"Unexpected error in email notification: {str(e)}",
            channel="email",
            details={"error": str(e)}
        )

def send_slack_notification(
    classification: str, 
    reasoning: str, 
    db: Session, 
    request_id
) -> bool:
    """
    Send Slack notification via webhook with retry logic and proper error handling.
    
    Args:
        classification: Content classification result
        reasoning: AI reasoning for classification
        db: Database session
        request_id: Request ID for logging
    
    Returns:
        True if Slack notification sent successfully, False otherwise
        
    Raises:
        NotificationServiceException: If Slack notification fails after retries
    """
    logger.info(
        f"Attempting to send Slack notification",
        extra={
            "request_id": request_id,
            "classification": classification,
            "channel": "slack"
        }
    )
    
    try:
        if not settings.slack_webhook_url:
            logger.warning(
                "Slack webhook URL not configured, using mock notification",
                extra={"request_id": request_id}
            )
            return _log_mock_notification(db, request_id, "slack", "sent")
            
        # Slack webhook integration with retry logic
        payload = {
            "text": f"🚨 Content Moderation Alert",
            "attachments": [
                {
                    "color": "danger" if classification != "safe" else "good",
                    "fields": [
                        {"title": "Classification", "value": classification.title(), "short": True},
                        {"title": "Reasoning", "value": reasoning, "short": False},
                        {"title": "Request ID", "value": str(request_id), "short": True}
                    ],
                    "footer": "Content Moderation System",
                    "ts": int(time.time())
                }
            ]
        }
        
        # Retry logic for webhook calls
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    settings.slack_webhook_url, 
                    json=payload, 
                    timeout=TIMEOUT
                )
                
                if response.status_code == 200:
                    logger.info(
                        "Slack notification sent successfully",
                        extra={
                            "request_id": request_id,
                            "attempt": attempt + 1
                        }
                    )
                    _log_notification_attempt(db, request_id, "slack", "sent")
                    return True
                else:
                    logger.warning(
                        f"Slack webhook returned status {response.status_code}",
                        extra={
                            "request_id": request_id,
                            "status_code": response.status_code,
                            "attempt": attempt + 1,
                            "response": response.text[:200]
                        }
                    )
                    
            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Slack webhook request failed on attempt {attempt + 1}",
                    extra={
                        "request_id": request_id,
                        "error": str(e),
                        "attempt": attempt + 1
                    }
                )
                
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                else:
                    raise NotificationServiceException(
                        f"Slack notification failed after {MAX_RETRIES} attempts: {str(e)}",
                        channel="slack",
                        details={"attempts": MAX_RETRIES, "error": str(e)}
                    )
        
        # If we get here, all retries failed
        _log_notification_attempt(db, request_id, "slack", "failed")
        return False
        
    except NotificationServiceException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in Slack notification",
            extra={
                "request_id": request_id,
                "error": str(e)
            },
            exc_info=True
        )
        _log_notification_attempt(db, request_id, "slack", "failed")
        raise NotificationServiceException(
            f"Unexpected error in Slack notification: {str(e)}",
            channel="slack",
            details={"error": str(e)}
        )

def _log_notification_attempt(
    db: Session, 
    request_id, 
    channel: str, 
    status: str
) -> None:
    """Log notification attempt to database."""
    try:
        log = NotificationLog(
            request_id=request_id,
            channel=channel,
            status=status
        )
        db.add(log)
        db.commit()
        
        logger.debug(
            f"Logged notification attempt",
            extra={
                "request_id": request_id,
                "channel": channel,
                "status": status
            }
        )
    except Exception as e:
        logger.error(
            f"Failed to log notification attempt",
            extra={
                "request_id": request_id,
                "channel": channel,
                "status": status,
                "error": str(e)
            }
        )
        db.rollback()

def _log_mock_notification(
    db: Session, 
    request_id, 
    channel: str, 
    status: str
) -> bool:
    """Log mock notification and return success."""
    _log_notification_attempt(db, request_id, channel, status)
    return True

def send_inappropriate_content_alert(
    to_email: str, 
    classification: str, 
    reasoning: str, 
    db: Session, 
    request_id
) -> None:
    """
    Send both email and Slack notifications for inappropriate content.
    
    Args:
        to_email: User email address
        classification: Content classification result
        reasoning: AI reasoning for classification
        db: Database session
        request_id: Request ID for logging
    """
    if classification == "safe":
        logger.debug(
            "Content classified as safe, skipping notifications",
            extra={"request_id": request_id, "classification": classification}
        )
        return
        
    logger.info(
        f"Sending inappropriate content alerts",
        extra={
            "request_id": request_id,
            "user_email": to_email,
            "classification": classification
        }
    )
    
    # Send email notification
    email_success = False
    try:
        email_success = send_email_notification(to_email, classification, reasoning, db, request_id)
    except NotificationServiceException as e:
        logger.error(
            f"Email notification failed",
            extra={
                "request_id": request_id,
                "user_email": to_email,
                "error": str(e)
            }
        )
    
    # Send Slack notification
    slack_success = False
    try:
        slack_success = send_slack_notification(classification, reasoning, db, request_id)
    except NotificationServiceException as e:
        logger.error(
            f"Slack notification failed",
            extra={
                "request_id": request_id,
                "error": str(e)
            }
        )
    
    logger.info(
        f"Notification results - Email: {email_success}, Slack: {slack_success}",
        extra={
            "request_id": request_id,
            "user_email": to_email,
            "email_success": email_success,
            "slack_success": slack_success
        }
    )
