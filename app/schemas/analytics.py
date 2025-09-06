from pydantic import BaseModel, EmailStr
from typing import Dict

class AnalyticsSummary(BaseModel):
    user: EmailStr
    total_requests: int
    breakdown: Dict[str, int]
