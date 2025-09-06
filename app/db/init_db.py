from app.db.session import engine
from app.models.moderation_request import ModerationRequest
from app.models.moderation_result import ModerationResult
from app.models.notification_log import NotificationLog

def init_db():
    print("Creating tables...")
    from app.db.session import Base
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    init_db()
