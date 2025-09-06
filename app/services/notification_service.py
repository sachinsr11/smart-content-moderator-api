from sqlalchemy.orm import Session

def send_inappropriate_content_alert(to_email: str, classification: str, reasoning: str, db: Session, request_id=None):
    # TODO: integrate Brevo here
    print(f"[MOCK ALERT] {to_email} flagged as {classification} because {reasoning}")
    return True
