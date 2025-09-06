import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from sqlalchemy.orm import relationship

class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    request_id = Column(UUID(as_uuid=True), ForeignKey("moderation_requests.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String, nullable=False)   # email/slack
    status = Column(String, nullable=False)    # sent/failed
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

    request = relationship("ModerationRequest", back_populates="notifications")
