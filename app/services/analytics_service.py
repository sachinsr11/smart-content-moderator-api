from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.moderation_request import ModerationRequest
from app.models.moderation_result import ModerationResult
from app.schemas.analytics import AnalyticsSummary

def get_user_summary(user_email: str, db: Session) -> AnalyticsSummary:
    total = db.query(func.count(ModerationRequest.id)).filter(
        ModerationRequest.user_email == user_email
    ).scalar()

    breakdown_query = db.query(
        ModerationResult.classification,
        func.count(ModerationResult.id)
    ).join(ModerationRequest).filter(
        ModerationRequest.user_email == user_email
    ).group_by(ModerationResult.classification).all()

    breakdown = {cls: count for cls, count in breakdown_query}

    return AnalyticsSummary(
        user=user_email,
        total_requests=total,
        breakdown=breakdown
    )
