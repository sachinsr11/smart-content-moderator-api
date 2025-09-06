class BrevoClient:
    def send_email(self, to_email: str, subject: str, content: str) -> bool:
        # TODO: implement real Brevo API call later
        print(f"[MOCK EMAIL] To: {to_email}, Subject: {subject}")
        return True
