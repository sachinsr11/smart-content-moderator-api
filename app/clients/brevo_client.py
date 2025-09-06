import requests
import os

class BrevoClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("BREVO_API_KEY")

    def send_email(self, to_email: str, subject: str, content: str) -> bool:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "sender": {"name": "Moderator", "email": "noreply@yourdomain.com"},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": content
        }
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 201