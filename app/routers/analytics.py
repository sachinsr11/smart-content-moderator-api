from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.analytics_service import get_user_summary
from app.schemas.analytics import AnalyticsSummary

router = APIRouter()

@router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(user: str, db: Session = Depends(get_db)):
    return get_user_summary(user, db)
