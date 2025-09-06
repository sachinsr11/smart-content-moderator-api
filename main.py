from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
from contextlib import asynccontextmanager

from app.routers import moderation, analytics
from app.core.logger import logger
from app.core.exceptions import ContentModeratorException, create_http_exception
from app.core.config import settings

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management for startup and shutdown events."""
    # Startup
    logger.info("Starting Content Moderator API", extra={"version": "1.0.0"})
    
    # Import all models to ensure they are registered with SQLAlchemy
    from app.models.moderation_request import ModerationRequest
    from app.models.moderation_result import ModerationResult
    from app.models.notification_log import NotificationLog
    
    # Initialize database if needed
    try:
        from app.db.session import engine, Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Content Moderator API")

# Create FastAPI application with comprehensive configuration
app = FastAPI(
    title="Smart Content Moderator API",
    description="""
    A comprehensive content moderation service that analyzes user-submitted content (text/images) 
    for inappropriate material using AI, stores results in a database, sends notifications via 
    email/Slack, and provides analytics data.
    
    ## Features
    
    * **AI-Powered Content Analysis**: Supports both OpenAI GPT-4 and Google Gemini
    * **Multi-Channel Notifications**: Email alerts via Brevo and Slack webhook notifications
    * **Comprehensive Analytics**: User-specific moderation statistics and breakdowns
    * **Async Processing**: Background task processing for notifications
    * **Security**: Rate limiting, input validation, and comprehensive error handling
    
    ## Authentication
    
    API keys are optional but recommended for production use. Include your API key in the 
    Authorization header: `Bearer your-api-key`
    
    ## Rate Limiting
    
    The API implements rate limiting to prevent abuse:
    - **100 requests per hour** per IP address
    - Rate limit headers are included in responses
    
    ## Error Handling
    
    All errors return structured JSON responses with:
    - `error_code`: Machine-readable error identifier
    - `message`: Human-readable error description
    - `details`: Additional error context
    """,
    version="1.0.0",
    contact={
        "name": "Content Moderator Support",
        "email": "support@contentmoderator.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # Configure appropriately for production
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to all requests for tracing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Add request ID to logger context
    logger.info(
        f"Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    logger.info(
        f"Request completed",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time": process_time
        }
    )
    
    return response

# Global exception handler
@app.exception_handler(ContentModeratorException)
async def content_moderator_exception_handler(request: Request, exc: ContentModeratorException):
    """Handle custom application exceptions."""
    logger.error(
        f"Content Moderator exception: {exc.message}",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "error_code": exc.error_code,
            "details": exc.details
        }
    )
    
    # Determine appropriate status code
    status_code = 500  # Default
    if hasattr(exc, '__class__'):
        from app.core.exceptions import EXCEPTION_STATUS_MAPPING
        status_code = EXCEPTION_STATUS_MAPPING.get(exc.__class__, 500)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": getattr(request.state, "request_id", "unknown")
        }
    )

# Include routers
app.include_router(moderation.router, tags=["moderation"])
app.include_router(analytics.router, tags=["analytics"])

# Health check endpoint
@app.get("/health", tags=["monitoring"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Health status and basic system information
    """
    try:
        # Check database connectivity
        from app.db.session import get_db
        db = next(get_db())
        db.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0",
            "services": {
                "database": "healthy",
                "api": "healthy"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
        )

# Metrics endpoint
@app.get("/metrics", tags=["monitoring"])
async def get_metrics():
    """
    Basic metrics endpoint for monitoring.
    
    Returns:
        Application metrics and statistics
    """
    try:
        from app.db.session import get_db
        from app.models.moderation_request import ModerationRequest
        from app.models.moderation_result import ModerationResult
        from sqlalchemy import func
        
        db = next(get_db())
        
        # Get basic statistics
        total_requests = db.query(func.count(ModerationRequest.id)).scalar()
        completed_requests = db.query(func.count(ModerationRequest.id)).filter(
            ModerationRequest.status == "completed"
        ).scalar()
        
        # Classification breakdown
        classification_stats = db.query(
            ModerationResult.classification,
            func.count(ModerationResult.id)
        ).group_by(ModerationResult.classification).all()
        
        return {
            "timestamp": time.time(),
            "total_requests": total_requests,
            "completed_requests": completed_requests,
            "completion_rate": completed_requests / total_requests if total_requests > 0 else 0,
            "classification_breakdown": dict(classification_stats),
            "uptime": "N/A"  # Would need to track start time
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to collect metrics",
                "message": str(e)
            }
        )

# Database initialization endpoint
@app.post("/api/v1/init-db", tags=["admin"])
async def init_database():
    """
    Initialize the database by creating all tables.
    
    This endpoint should only be used in development or for initial setup.
    In production, use proper database migrations.
    
    Returns:
        Success or error message
    """
    try:
        from app.db.session import engine, Base
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully via API")
        
        return {
            "message": "Database tables created successfully!",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}", exc_info=True)
        return {
            "error": f"Failed to create tables: {str(e)}",
            "timestamp": time.time()
        }

# Root endpoint
@app.get("/", tags=["general"])
async def root():
    """
    Root endpoint with API information.
    
    Returns:
        Basic API information and links
    """
    return {
        "message": "Smart Content Moderator API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
        "endpoints": {
            "text_moderation": "/api/v1/moderate/text",
            "image_moderation": "/api/v1/moderate/image",
            "analytics": "/api/v1/analytics/summary"
        }
    }
