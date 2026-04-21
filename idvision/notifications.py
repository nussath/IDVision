import os
import smtplib
import ssl
import threading
from email.message import EmailMessage

EMAIL_ENABLED = os.environ.get("EMAIL_ENABLED", "false").lower() in ("1", "true", "yes", "on")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ALERT_EMAIL_TO = [
    addr.strip() for addr in os.environ.get("ALERT_EMAIL_TO", "").split(",") if addr.strip()
]
ALERT_EMAIL_FROM = os.environ.get("ALERT_EMAIL_FROM") or SMTP_USER


def _is_configured():
    return bool(EMAIL_ENABLED and SMTP_USER and SMTP_PASSWORD and ALERT_EMAIL_TO)


def _send(message: EmailMessage):
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(message)
        print(f"[notifications] Email sent to {', '.join(ALERT_EMAIL_TO)}")
    except Exception as e:
        print(f"[notifications] Email send failed: {e}")


def send_alert_email(name: str, category: str, timestamp: str):
    """Non-blocking: spawns a thread to send via SMTP. Silently no-ops if
    email isn't configured."""
    if not _is_configured():
        return False

    msg = EmailMessage()
    msg["Subject"] = f"IDVision alert: {category} detected — {name}"
    msg["From"] = ALERT_EMAIL_FROM
    msg["To"] = ", ".join(ALERT_EMAIL_TO)
    msg.set_content(
        f"IDVision detection alert\n\n"
        f"Name:     {name}\n"
        f"Category: {category}\n"
        f"Time:     {timestamp}\n\n"
        f"This is an automated message from the IDVision surveillance system."
    )

    threading.Thread(target=_send, args=(msg,), daemon=True).start()
    return True
