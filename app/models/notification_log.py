import uuid
from datetime import datetime
from sqlalchemy import Column, String, Enum, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.db.session import Base


class NotificationStatus(str, enum.Enum):
    sent = "sent"
    failed = "failed"


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    request_id = Column(UUID(as_uuid=True), ForeignKey("moderation_requests.id", ondelete="CASCADE"), nullable=False)

    channel = Column(String, nullable=False, default="email")  # "email" for Brevo
    status = Column(Enum(NotificationStatus), default=NotificationStatus.sent)
    sent_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    request = relationship("ModerationRequest", back_populates="notifications")
