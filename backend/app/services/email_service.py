import os
import smtplib
from email.message import EmailMessage


def send_welcome_email(*, recipient: str, name: str) -> tuple[bool, str]:
    """Send a ResearchMate AI welcome email.

    SMTP is optional at code level, but must be configured in backend/.env
    for the registration email to actually be delivered.
    Returns (sent, reason). Never raises for SMTP/configuration failures.
    """
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", username).strip()

    if not username or not password or not sender:
        return False, "SMTP is not configured."

    msg = EmailMessage()
    msg["Subject"] = "Welcome to ResearchMate AI"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content(
        f"Hi {name},\n\n"
        "Welcome to ResearchMate AI! Your research workspace has been created successfully.\n\n"
        "You can now discover research topics, organize literature, write your manuscript, review it, and prepare it for publication.\n\n"
        "Your account email: {recipient}\n\n"
        "Regards,\nResearchMate AI"
    )

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.send_message(msg)
        return True, "Welcome email sent."
    except Exception as exc:
        return False, f"Email delivery failed: {exc}"
