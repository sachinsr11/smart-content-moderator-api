import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class ModerationResult(Base):
    __tablename__ = "moderation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    request_id = Column(UUID(as_uuid=True), ForeignKey("moderation_requests.id", ondelete="CASCADE"), nullable=False)

    classification = Column(String, nullable=False)  # toxic, spam, harassment, safe
    confidence = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    llm_response = Column(JSON, nullable=True)  # store raw LLM response

    # Relationship
    request = relationship("ModerationRequest", back_populates="results")
