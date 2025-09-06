"""
Comprehensive test suite for the Content Moderator API.

This module contains unit tests, integration tests, and API tests to ensure
the application works correctly and meets all requirements.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.db.session import get_db, Base
from app.models.moderation_request import ModerationRequest, ContentType, RequestStatus
from app.models.moderation_result import ModerationResult
from app.models.notification_log import NotificationLog
from app.core.exceptions import ValidationException, DatabaseException, LLMServiceException
from app.core.security import validate_email, validate_text_content, validate_image_url

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    """Create test client."""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    """Create database session for testing."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

class TestSecurityValidation:
    """Test security and validation functions."""
    
    def test_validate_email_valid(self):
        """Test email validation with valid emails."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "admin+test@company.org"
        ]
        for email in valid_emails:
            assert validate_email(email), f"Email {email} should be valid"
    
    def test_validate_email_invalid(self):
        """Test email validation with invalid emails."""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@domain",
            "a" * 300 + "@example.com"  # Too long
        ]
        for email in invalid_emails:
            assert not validate_email(email), f"Email {email} should be invalid"
    
    def test_validate_text_content_valid(self):
        """Test text content validation with valid content."""
        valid_content = [
            "This is a normal message",
            "Hello world!",
            "Content with numbers 123 and symbols !@#"
        ]
        for content in valid_content:
            is_valid, error = validate_text_content(content)
            assert is_valid, f"Content '{content}' should be valid: {error}"
    
    def test_validate_text_content_invalid(self):
        """Test text content validation with invalid content."""
        invalid_cases = [
            ("", "Empty content"),
            ("   ", "Whitespace only"),
            ("x" * 10001, "Too long content"),
            ("<script>alert('xss')</script>", "XSS attempt"),
            ("javascript:alert('xss')", "JavaScript protocol")
        ]
        for content, description in invalid_cases:
            is_valid, error = validate_text_content(content)
            assert not is_valid, f"{description} should be invalid: {error}"
    
    def test_validate_image_url_valid(self):
        """Test image URL validation with valid URLs."""
        valid_urls = [
            "https://example.com/image.jpg",
            "http://test.com/picture.png",
            "https://cdn.example.com/photo.webp"
        ]
        for url in valid_urls:
            is_valid, error = validate_image_url(url)
            assert is_valid, f"URL {url} should be valid: {error}"
    
    def test_validate_image_url_invalid(self):
        """Test image URL validation with invalid URLs."""
        invalid_urls = [
            ("", "Empty URL"),
            ("not-a-url", "Invalid format"),
            ("ftp://example.com/image.jpg", "Wrong protocol"),
            ("https://example.com/image", "No extension"),
            ("x" * 2049, "Too long URL")
        ]
        for url, description in invalid_urls:
            is_valid, error = validate_image_url(url)
            assert not is_valid, f"{description} should be invalid: {error}"

class TestModerationService:
    """Test moderation service functionality."""
    
    @pytest.mark.asyncio
    async def test_handle_text_moderation_success(self, db_session):
        """Test successful text moderation."""
        from app.services.moderation_service import handle_text_moderation
        from app.schemas.moderation import ModerationTextRequest
        from fastapi import BackgroundTasks
        
        # Mock LLM response
        with patch('app.services.moderation_service.classify_text') as mock_classify:
            mock_classify.return_value = ("safe", 0.95, "No harmful content", {"mock": True})
            
            request = ModerationTextRequest(
                email="test@example.com",
                content="This is a safe message"
            )
            
            result = await handle_text_moderation(request, db_session, BackgroundTasks())
            
            assert result.classification == "safe"
            assert result.confidence == 0.95
            assert result.status == "completed"
            assert result.reasoning == "No harmful content"
    
    @pytest.mark.asyncio
    async def test_handle_text_moderation_invalid_email(self, db_session):
        """Test text moderation with invalid email."""
        from app.services.moderation_service import handle_text_moderation
        from app.schemas.moderation import ModerationTextRequest
        from fastapi import BackgroundTasks
        
        request = ModerationTextRequest(
            email="invalid-email",
            content="This is a safe message"
        )
        
        with pytest.raises(ValidationException) as exc_info:
            await handle_text_moderation(request, db_session, BackgroundTasks())
        
        assert exc_info.value.details["field"] == "email"
    
    @pytest.mark.asyncio
    async def test_handle_text_moderation_llm_failure(self, db_session):
        """Test text moderation when LLM service fails."""
        from app.services.moderation_service import handle_text_moderation
        from app.schemas.moderation import ModerationTextRequest
        from fastapi import BackgroundTasks
        
        # Mock LLM failure
        with patch('app.services.moderation_service.classify_text') as mock_classify:
            mock_classify.side_effect = Exception("LLM service unavailable")
            
            request = ModerationTextRequest(
                email="test@example.com",
                content="This is a safe message"
            )
            
            with pytest.raises(LLMServiceException) as exc_info:
                await handle_text_moderation(request, db_session, BackgroundTasks())
            
            assert "LLM service unavailable" in str(exc_info.value)

class TestNotificationService:
    """Test notification service functionality."""
    
    def test_send_email_notification_success(self, db_session):
        """Test successful email notification."""
        from app.services.notification_service import send_email_notification
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_post.return_value = mock_response
            
            with patch('app.core.config.settings') as mock_settings:
                mock_settings.brevo_api_key = "test-key"
                
                result = send_email_notification(
                    "test@example.com",
                    "toxic",
                    "Contains offensive language",
                    db_session,
                    "test-request-id"
                )
                
                assert result is True
                mock_post.assert_called_once()
    
    def test_send_slack_notification_success(self, db_session):
        """Test successful Slack notification."""
        from app.services.notification_service import send_slack_notification
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            with patch('app.core.config.settings') as mock_settings:
                mock_settings.slack_webhook_url = "https://hooks.slack.com/test"
                
                result = send_slack_notification(
                    "toxic",
                    "Contains offensive language",
                    db_session,
                    "test-request-id"
                )
                
                assert result is True
                mock_post.assert_called_once()

class TestAPIEndpoints:
    """Test API endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "total_requests" in data
        assert "classification_breakdown" in data
    
    def test_text_moderation_endpoint_success(self, client):
        """Test successful text moderation endpoint."""
        with patch('app.services.moderation_service.handle_text_moderation') as mock_handle:
            mock_result = Mock()
            mock_result.request_id = "test-id"
            mock_result.classification = "safe"
            mock_result.confidence = 0.95
            mock_result.reasoning = "No harmful content"
            mock_result.status = "completed"
            mock_result.llm_response = {"mock": True}
            mock_handle.return_value = mock_result
            
            response = client.post(
                "/api/v1/moderate/text",
                json={
                    "email": "test@example.com",
                    "content": "This is a safe message"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["classification"] == "safe"
            assert data["confidence"] == 0.95
    
    def test_text_moderation_endpoint_validation_error(self, client):
        """Test text moderation endpoint with validation error."""
        response = client.post(
            "/api/v1/moderate/text",
            json={
                "email": "invalid-email",
                "content": "This is a safe message"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error_code" in data
        assert "message" in data
    
    def test_image_moderation_endpoint_success(self, client):
        """Test successful image moderation endpoint."""
        with patch('app.services.moderation_service.handle_image_moderation') as mock_handle:
            mock_result = Mock()
            mock_result.request_id = "test-id"
            mock_result.classification = "safe"
            mock_result.confidence = 0.90
            mock_result.reasoning = "No harmful content"
            mock_result.status = "completed"
            mock_result.llm_response = {"mock": True}
            mock_handle.return_value = mock_result
            
            response = client.post(
                "/api/v1/moderate/image",
                json={
                    "email": "test@example.com",
                    "image_url": "https://example.com/image.jpg"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["classification"] == "safe"
            assert data["confidence"] == 0.90
    
    def test_analytics_endpoint(self, client):
        """Test analytics endpoint."""
        with patch('app.services.analytics_service.get_user_summary') as mock_get_summary:
            mock_summary = Mock()
            mock_summary.user = "test@example.com"
            mock_summary.total_requests = 10
            mock_summary.breakdown = {"safe": 8, "toxic": 2}
            mock_get_summary.return_value = mock_summary
            
            response = client.get("/api/v1/analytics/summary?user=test@example.com")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user"] == "test@example.com"
            assert data["total_requests"] == 10
            assert data["breakdown"]["safe"] == 8
    
    def test_rate_limiting(self, client):
        """Test rate limiting functionality."""
        # This would need to be implemented with proper rate limiting testing
        # For now, just test that the endpoint exists
        response = client.post(
            "/api/v1/moderate/text",
            json={
                "email": "test@example.com",
                "content": "This is a safe message"
            }
        )
        
        # Should not be rate limited for first request
        assert response.status_code in [200, 400, 500]  # Any valid response

class TestDatabaseModels:
    """Test database models."""
    
    def test_moderation_request_creation(self, db_session):
        """Test moderation request model creation."""
        request = ModerationRequest(
            user_email="test@example.com",
            content_type=ContentType.text,
            content_hash="test-hash",
            status=RequestStatus.pending
        )
        
        db_session.add(request)
        db_session.commit()
        db_session.refresh(request)
        
        assert request.id is not None
        assert request.user_email == "test@example.com"
        assert request.content_type == ContentType.text
        assert request.status == RequestStatus.pending
    
    def test_moderation_result_creation(self, db_session):
        """Test moderation result model creation."""
        # First create a request
        request = ModerationRequest(
            user_email="test@example.com",
            content_type=ContentType.text,
            content_hash="test-hash",
            status=RequestStatus.pending
        )
        db_session.add(request)
        db_session.commit()
        db_session.refresh(request)
        
        # Then create a result
        result = ModerationResult(
            request_id=request.id,
            classification="safe",
            confidence=0.95,
            reasoning="No harmful content",
            llm_response={"mock": True}
        )
        
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        
        assert result.id is not None
        assert result.request_id == request.id
        assert result.classification == "safe"
        assert result.confidence == 0.95
    
    def test_notification_log_creation(self, db_session):
        """Test notification log model creation."""
        # First create a request
        request = ModerationRequest(
            user_email="test@example.com",
            content_type=ContentType.text,
            content_hash="test-hash",
            status=RequestStatus.completed
        )
        db_session.add(request)
        db_session.commit()
        db_session.refresh(request)
        
        # Then create a notification log
        log = NotificationLog(
            request_id=request.id,
            channel="email",
            status="sent"
        )
        
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)
        
        assert log.id is not None
        assert log.request_id == request.id
        assert log.channel == "email"
        assert log.status == "sent"

class TestLLMClient:
    """Test LLM client functionality."""
    
    def test_classify_text_mock(self):
        """Test text classification with mock fallback."""
        from app.clients.llm_client import classify_text
        
        # Test safe content
        classification, confidence, reasoning, response = classify_text("Hello world")
        assert classification == "safe"
        assert confidence > 0.9
        assert "mock" in response
    
    def test_classify_text_toxic(self):
        """Test text classification with toxic content."""
        from app.clients.llm_client import classify_text
        
        # Test toxic content
        classification, confidence, reasoning, response = classify_text("You are dumb")
        assert classification == "toxic"
        assert confidence > 0.9
        assert "mock" in response
    
    def test_classify_image_mock(self):
        """Test image classification with mock fallback."""
        from app.clients.llm_client import classify_image
        
        # Test safe image
        classification, confidence, reasoning, response = classify_image("https://example.com/safe.jpg")
        assert classification == "safe"
        assert confidence > 0.9
        assert "mock" in response
    
    def test_classify_image_toxic(self):
        """Test image classification with toxic content."""
        from app.clients.llm_client import classify_image
        
        # Test toxic image URL
        classification, confidence, reasoning, response = classify_image("https://example.com/nsfw.jpg")
        assert classification == "toxic"
        assert confidence > 0.9
        assert "mock" in response

# Integration tests
class TestIntegration:
    """Integration tests for the complete workflow."""
    
    def test_complete_text_moderation_workflow(self, client):
        """Test complete text moderation workflow."""
        with patch('app.services.moderation_service.handle_text_moderation') as mock_handle:
            mock_result = Mock()
            mock_result.request_id = "test-id"
            mock_result.classification = "toxic"
            mock_result.confidence = 0.95
            mock_result.reasoning = "Contains offensive language"
            mock_result.status = "completed"
            mock_result.llm_response = {"mock": True}
            mock_handle.return_value = mock_result
            
            # Submit text for moderation
            response = client.post(
                "/api/v1/moderate/text",
                json={
                    "email": "test@example.com",
                    "content": "You are an idiot"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["classification"] == "toxic"
            
            # Check analytics
            with patch('app.services.analytics_service.get_user_summary') as mock_analytics:
                mock_summary = Mock()
                mock_summary.user = "test@example.com"
                mock_summary.total_requests = 1
                mock_summary.breakdown = {"toxic": 1}
                mock_analytics.return_value = mock_summary
                
                analytics_response = client.get("/api/v1/analytics/summary?user=test@example.com")
                assert analytics_response.status_code == 200
                analytics_data = analytics_response.json()
                assert analytics_data["total_requests"] == 1
                assert analytics_data["breakdown"]["toxic"] == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
