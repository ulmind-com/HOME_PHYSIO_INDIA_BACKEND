"""SMTP email service using aiosmtplib + Jinja2 templates.

Designed to be scheduled via FastAPI ``BackgroundTasks`` so the request path is
never blocked by SMTP latency. When SMTP is not configured the service logs the
message instead of raising, so local development works without credentials.
"""

from __future__ import annotations

from email.message import EmailMessage
from typing import Any, Dict, Optional

import aiosmtplib
from jinja2 import Environment, select_autoescape

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_jinja = Environment(autoescape=select_autoescape(["html", "xml"]))

_BASE_TEMPLATE = """\
<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;border:1px solid #eee;border-radius:8px;overflow:hidden">
  <div style="background:#0f766e;color:#fff;padding:20px 24px">
    <h2 style="margin:0">{{ brand }}</h2>
  </div>
  <div style="padding:24px;color:#333;line-height:1.6">
    {{ body }}
  </div>
  <div style="background:#f9fafb;color:#888;padding:16px 24px;font-size:12px">
    &copy; {{ brand }}. This is an automated message, please do not reply.
  </div>
</div>
"""


class EmailService:
    """Send transactional emails over SMTP."""

    def __init__(self) -> None:
        self.enabled = settings.email_enabled

    def _render(self, body_html: str) -> str:
        template = _jinja.from_string(_BASE_TEMPLATE)
        return template.render(brand=settings.SMTP_FROM_NAME, body=body_html)

    async def send(
        self,
        to: str,
        subject: str,
        body_html: str,
        text_fallback: Optional[str] = None,
    ) -> bool:
        """Send a single HTML email. Returns ``True`` on success."""
        if not self.enabled:
            logger.info(
                "Email disabled; skipping send",
                extra={"to": to, "subject": subject},
            )
            return False

        message = EmailMessage()
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text_fallback or "Please view this email in HTML.")
        message.add_alternative(self._render(body_html), subtype="html")

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=settings.SMTP_TLS,
                use_tls=settings.SMTP_SSL,
                timeout=30,
            )
            logger.info("Email sent", extra={"to": to, "subject": subject})
            return True
        except Exception as exc:  # noqa: BLE001 - never break the request path
            logger.error(
                "Email send failed",
                extra={"to": to, "subject": subject, "error": str(exc)},
            )
            return False

    # ---- Convenience templated senders ----

    async def send_booking_confirmation(self, to: str, context: Dict[str, Any]) -> bool:
        body = (
            f"<p>Dear {context.get('name', 'Customer')},</p>"
            f"<p>Thank you for booking <b>{context.get('service')}</b> with us.</p>"
            f"<p>Your booking reference is <b>{context.get('reference')}</b>.</p>"
            f"<p>Preferred date: <b>{context.get('date')}</b></p>"
            "<p>Our team will contact you shortly to confirm the details.</p>"
        )
        return await self.send(to, "Your Booking is Received", body)

    async def send_contact_confirmation(self, to: str, context: Dict[str, Any]) -> bool:
        body = (
            f"<p>Dear {context.get('name', 'there')},</p>"
            "<p>We have received your message and will get back to you soon.</p>"
            f"<blockquote>{context.get('message', '')}</blockquote>"
        )
        return await self.send(to, "We Received Your Message", body)

    async def send_application_confirmation(self, to: str, context: Dict[str, Any]) -> bool:
        body = (
            f"<p>Dear {context.get('name', 'Applicant')},</p>"
            f"<p>Thank you for applying for <b>{context.get('job')}</b>.</p>"
            f"<p>Your application reference is <b>{context.get('reference')}</b>.</p>"
            "<p>Our HR team will review your application and reach out if shortlisted.</p>"
        )
        return await self.send(to, "Application Received", body)

    async def send_password_reset(self, to: str, reset_link: str) -> bool:
        body = (
            "<p>We received a request to reset your password.</p>"
            f'<p><a href="{reset_link}" '
            'style="background:#0f766e;color:#fff;padding:10px 18px;'
            'border-radius:6px;text-decoration:none">Reset Password</a></p>'
            f"<p>Or copy this link: {reset_link}</p>"
            "<p>If you did not request this, you can safely ignore this email.</p>"
        )
        return await self.send(to, "Password Reset Request", body)

    async def send_admin_notification(self, subject: str, body_html: str) -> bool:
        if not settings.ADMIN_NOTIFICATION_EMAIL:
            return False
        return await self.send(settings.ADMIN_NOTIFICATION_EMAIL, subject, body_html)


# Module-level singleton.
email_service = EmailService()
