import uuid
from datetime import datetime
from sqlalchemy import Column, String, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.db.session import Base


class ContentType(str, enum.Enum):
    text = "text"
    image = "image"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class ModerationRequest(Base):
    __tablename__ = "moderation_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_email = Column(String, nullable=False, index=True)
    content_type = Column(Enum(ContentType), nullable=False)
    content_hash = Column(String, nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    results = relationship("ModerationResult", back_populates="request", cascade="all, delete-orphan")
    notifications = relationship("NotificationLog", back_populates="request", cascade="all, delete-orphan")
