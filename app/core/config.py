from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Smart Content Moderator API"
    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/moderator"
    openai_api_key: str | None = None
    slack_webhook_url: str | None = None
    brevo_api_key: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
