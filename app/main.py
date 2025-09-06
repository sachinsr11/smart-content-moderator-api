from fastapi import FastAPI
from app.routers import moderation, analytics

app = FastAPI(title="Smart Content Moderator API")

# Include routers
app.include_router(moderation.router, prefix="/api/v1/moderate", tags=["moderation"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
