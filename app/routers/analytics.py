from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.analytics_service import get_user_summary
from app.schemas.analytics import AnalyticsSummary

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@router.get("/summary", response_model=AnalyticsSummary, status_code=200)
async def analytics_summary(user: str, db: Session = Depends(get_db)):
    try:
        return get_user_summary(user, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics retrieval failed: {str(e)}")
