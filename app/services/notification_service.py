from app.db.session import get_db
from app.models.notification_log import NotificationLog
from sqlalchemy.orm import Session
import smtplib  # or a service like SendGrid

def send_inappropriate_content_alert(to_email: str, classification: str, reasoning: str, db: Session, request_id):
    # Log in DB
    log = NotificationLog(
        user_email=to_email,
        request_id=request_id,
        classification=classification,
        message=f"Content flagged as {classification}: {reasoning}"
    )
    db.add(log)
    db.commit()

    # Send email / alert (mock for now)
    print(f"Sending notification to {to_email}: {classification} - {reasoning}")
