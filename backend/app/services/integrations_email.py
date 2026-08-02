"""SMTP adapter + demo email queue (CommsMessage channel=email)."""
from __future__ import annotations

import smtplib
import time
from email.message import EmailMessage
from typing import Any

from app.core.config import settings


def send_email(to_email: str, subject: str, body: str) -> dict[str, Any]:
    """Live SMTP when configured; otherwise demo-queued success (ERP outbox)."""
    to_email = (to_email or "").strip()
    if not to_email:
        return {"provider": "email", "live": False, "status": "failed", "error": "to_email required"}

    if not settings.smtp_live:
        return {
            "provider": "email_demo",
            "live": False,
            "demo": True,
            "status": "queued_sent",
            "message_id": f"eml.DEMO{int(time.time())}",
            "to": to_email,
            "subject": subject,
            "note": "SMTP not set — stored in Comms outbox as demo-sent (full process).",
        }

    msg = EmailMessage()
    msg["Subject"] = subject or "(no subject)"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_email
    msg.set_content(body or "")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return {
            "provider": "smtp",
            "live": True,
            "status": "sent",
            "message_id": f"eml.{int(time.time())}",
            "to": to_email,
            "subject": subject,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "provider": "smtp",
            "live": True,
            "status": "failed",
            "error": str(exc)[:240],
            "to": to_email,
        }
