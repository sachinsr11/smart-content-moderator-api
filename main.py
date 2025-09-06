from fastapi import FastAPI
from app.routers import moderation, analytics

app = FastAPI(title="Smart Content Moderator API")

# Import all models to ensure they are registered with SQLAlchemy
from app.db.base import *  # This imports all models

# Include routers
app.include_router(moderation.router, tags=["moderation"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])

# Add database initialization endpoint
@app.post("/api/v1/init-db")
def init_database():
    """Initialize the database by creating all tables."""
    try:
        from app.db.session import engine, Base
        Base.metadata.create_all(bind=engine)
        return {"message": "Database tables created successfully!"}
    except Exception as e:
        return {"error": f"Failed to create tables: {str(e)}"}
