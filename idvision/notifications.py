import mimetypes
import os
import smtplib
import ssl
import threading
from email.message import EmailMessage
from pathlib import Path

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


def configuration_status():
    """Human-readable description of what's missing for email delivery."""
    problems = []
    if not EMAIL_ENABLED:
        problems.append("EMAIL_ENABLED is not true")
    if not SMTP_USER:
        problems.append("SMTP_USER is empty")
    if not SMTP_PASSWORD:
        problems.append("SMTP_PASSWORD is empty")
    if not ALERT_EMAIL_TO:
        problems.append("ALERT_EMAIL_TO is empty")
    return problems


def _attach_file(message: EmailMessage, path_str: str):
    path = Path(path_str)
    if not path.is_file():
        return
    ctype, _ = mimetypes.guess_type(path.name)
    if not ctype:
        ctype = "application/octet-stream"
    maintype, _, subtype = ctype.partition("/")
    message.add_attachment(
        path.read_bytes(),
        maintype=maintype,
        subtype=subtype or "octet-stream",
        filename=path.name,
    )


def _send_sync(message: EmailMessage):
    """Blocking send. Returns (ok: bool, error_message: str|None)."""
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            refused = server.send_message(message)
        if refused:
            return False, f"Server refused recipients: {refused}"
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _send(message: EmailMessage):
    """Non-blocking variant used by the camera loop. Prints outcome to stdout."""
    ok, err = _send_sync(message)
    if ok:
        print(f"[notifications] Email sent to {', '.join(ALERT_EMAIL_TO)}")
    else:
        print(f"[notifications] Email send failed: {err}")


def send_alert_email(name: str, category: str, timestamp: str,
                     location: str = None, snapshot_path: str = None):
    """Non-blocking: spawn a thread to send via SMTP. Silent no-op if
    email isn't configured. Attaches the snapshot JPEG if provided."""
    if not _is_configured():
        return False

    msg = EmailMessage()
    msg["Subject"] = f"IDVision alert: {category} detected — {name}"
    msg["From"] = ALERT_EMAIL_FROM
    msg["To"] = ", ".join(ALERT_EMAIL_TO)

    body_lines = [
        "IDVision detection alert",
        "",
        f"Name:     {name}",
        f"Category: {category}",
        f"Time:     {timestamp}",
    ]
    if location:
        body_lines.append(f"Location: {location}")
    if snapshot_path:
        body_lines.append(f"Snapshot: attached ({Path(snapshot_path).name})")
    body_lines += [
        "",
        "This is an automated message from the IDVision surveillance system.",
    ]
    msg.set_content("\n".join(body_lines))

    if snapshot_path:
        _attach_file(msg, snapshot_path)

    threading.Thread(target=_send, args=(msg,), daemon=True).start()
    return True


def send_test_email():
    """Send a test message synchronously so the admin page can surface the
    real SMTP outcome (not just a fire-and-forget ack). Returns (ok, message)."""
    problems = configuration_status()
    if problems:
        return False, "Email not configured: " + "; ".join(problems)

    msg = EmailMessage()
    msg["Subject"] = "IDVision test email"
    msg["From"] = ALERT_EMAIL_FROM
    msg["To"] = ", ".join(ALERT_EMAIL_TO)
    msg.set_content(
        "This is a test message from the IDVision dashboard. "
        "If you received it, SMTP delivery is working."
    )
    ok, err = _send_sync(msg)
    if ok:
        return True, (
            f"Test email accepted by {SMTP_HOST} for "
            f"{', '.join(ALERT_EMAIL_TO)}. If it does not arrive within a "
            "minute, check the Spam folder or the recipient's server quarantine."
        )
    return False, f"SMTP error: {err}"
