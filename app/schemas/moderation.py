from pydantic import BaseModel, EmailStr
from uuid import UUID
from typing import Optional, Literal, Dict


# ---- Requests ----
class ModerationTextRequest(BaseModel):
    email: EmailStr
    content: str


class ModerationImageRequest(BaseModel):
    email: EmailStr
    image_url: str  # simplify to URL; base64 can be a stretch goal


# ---- Responses ----
class ModerationResultResponse(BaseModel):
    request_id: UUID
    classification: Literal["toxic", "spam", "harassment", "safe"]
    confidence: Optional[float] = None
    reasoning: Optional[str] = None
    status: str
    llm_response: Optional[Dict] = None

    class Config:
        from_attributes = True
