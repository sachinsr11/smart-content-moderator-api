# Smart Content Moderator API

A comprehensive content moderation service that analyzes user-submitted content (text/images) for inappropriate material using AI, stores results in a database, sends notifications via email/Slack, and provides analytics data.

## Features

- **AI-Powered Content Analysis**: Supports both OpenAI GPT-4 and Google Gemini for text and image classification
- **Multi-Channel Notifications**: Email alerts via Brevo and Slack webhook notifications
- **Comprehensive Analytics**: User-specific moderation statistics and breakdowns
- **Async Processing**: Background task processing for notifications
- **Docker Support**: Multi-stage Dockerfile and Docker Compose for easy deployment
- **Database Integration**: PostgreSQL with SQLAlchemy ORM and Alembic migrations

## API Endpoints

### Content Moderation
- `POST /api/v1/moderate/text` - Analyze text content
- `POST /api/v1/moderate/image` - Analyze image content

### Analytics
- `GET /api/v1/analytics/summary?user=email@example.com` - Get user analytics

### Database Management
- `POST /api/v1/init-db` - Initialize database tables

## Database Schema

### moderation_requests
- `id` (UUID) - Primary key
- `user_email` (String) - User's email address
- `content_type` (Enum) - "text" or "image"
- `content_hash` (String) - SHA256 hash of content
- `status` (Enum) - "pending", "completed", "failed"
- `created_at` (DateTime) - Creation timestamp

### moderation_results
- `id` (UUID) - Primary key
- `request_id` (UUID) - Foreign key to moderation_requests
- `classification` (String) - "toxic", "spam", "harassment", "safe"
- `confidence` (Float) - AI confidence score (0-1)
- `reasoning` (Text) - AI explanation
- `llm_response` (JSON) - Raw LLM response

### notification_logs
- `id` (UUID) - Primary key
- `request_id` (UUID) - Foreign key to moderation_requests
- `channel` (String) - "email" or "slack"
- `status` (String) - "sent" or "failed"
- `sent_at` (DateTime) - Notification timestamp

## Setup Instructions

### 1. Environment Configuration

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your actual API keys:
- `OPENAI_API_KEY` or `GEMINI_API_KEY` (at least one required)
- `SLACK_WEBHOOK_URL` (optional)
- `BREVO_API_KEY` (optional)

### 2. Docker Deployment (Recommended)

```bash
# Start the application with Docker Compose
docker-compose up -d

# Initialize the database
curl -X POST http://localhost:8000/api/v1/init-db
```

### 3. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL database
# Update DATABASE_URL in .env

# Run database migrations
alembic upgrade head

# Start the application
uvicorn main:app --reload
```

## Usage Examples

### Text Moderation

```bash
curl -X POST "http://localhost:8000/api/v1/moderate/text" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "content": "This is a test message"
  }'
```

### Image Moderation

```bash
curl -X POST "http://localhost:8000/api/v1/moderate/image" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "image_url": "https://example.com/image.jpg"
  }'
```

### Analytics

```bash
curl "http://localhost:8000/api/v1/analytics/summary?user=user@example.com"
```

## Response Format

### Moderation Response
```json
{
  "request_id": "uuid",
  "classification": "safe|toxic|spam|harassment",
  "confidence": 0.95,
  "reasoning": "AI explanation",
  "status": "completed",
  "llm_response": {...}
}
```

### Analytics Response
```json
{
  "user": "user@example.com",
  "total_requests": 10,
  "breakdown": {
    "safe": 8,
    "toxic": 1,
    "spam": 1
  }
}
```

## Configuration

The application supports multiple LLM providers with automatic fallback:

1. **OpenAI GPT-4** (preferred for text and images)
2. **Google Gemini** (fallback for text)
3. **Mock responses** (when no API keys are configured)

## Notification Channels

### Email (Brevo)
- Sends HTML-formatted emails to users when inappropriate content is detected
- Configurable sender information and templates

### Slack
- Posts formatted messages to configured Slack channel
- Includes classification, reasoning, and visual indicators

## Development

### Project Structure
```
app/
├── clients/          # External API clients (LLM, email, Slack)
├── core/            # Configuration and logging
├── db/              # Database session and base models
├── models/          # SQLAlchemy models
├── routers/         # FastAPI route handlers
├── schemas/         # Pydantic request/response models
├── services/        # Business logic
└── utils/           # Utility functions
```

### Adding New LLM Providers

1. Add provider-specific functions in `app/clients/llm_client.py`
2. Update the provider selection logic in `classify_text()` and `classify_image()`
3. Add environment variable for API key in `app/core/config.py`

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
