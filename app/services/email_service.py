"""Resend email service using Jinja2 templates.

Designed to be scheduled via FastAPI ``BackgroundTasks``. 
When Resend is not configured the service logs the message instead of raising, 
so local development works without credentials.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import asyncio
import resend

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
    {{ body | safe }}
  </div>
  <div style="background:#f9fafb;color:#888;padding:16px 24px;font-size:12px">
    &copy; {{ brand }}. This is an automated message, please do not reply.
  </div>
</div>
"""


class EmailService:
    """Send transactional emails over Resend API."""

    def __init__(self) -> None:
        self.enabled = settings.email_enabled
        if self.enabled:
            resend.api_key = settings.RESEND_API_KEY

    def _render(self, body_html: str) -> str:
        template = _jinja.from_string(_BASE_TEMPLATE)
        return template.render(brand=settings.APP_NAME, body=body_html)

    def _sync_send(self, to: str, subject: str, body_html: str, text_fallback: Optional[str]) -> bool:
        try:
            params = {
                "from": f"{settings.APP_NAME} <{settings.MAIL_ADDRESS}>",
                "to": [to],
                "subject": subject,
                "html": self._render(body_html),
            }
            if text_fallback:
                params["text"] = text_fallback
            
            resend.Emails.send(params)
            logger.info("Email sent via Resend", extra={"to": to, "subject": subject})
            return True
        except Exception as exc:
            logger.error(
                "Email send failed via Resend",
                extra={"to": to, "subject": subject, "error": str(exc)},
            )
            return False

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

        # Resend Python SDK is synchronous, so we run it in a thread to avoid blocking the event loop
        return await asyncio.to_thread(self._sync_send, to, subject, body_html, text_fallback)

    # ---- Convenience templated senders ----

    async def send_welcome_email(self, to: str, name: str) -> bool:
        body = f"""
        <div style="text-align: center; padding: 32px 20px;">
            <div style="background-color: #f0fdfa; display: inline-block; padding: 16px; border-radius: 50%; margin-bottom: 24px;">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#0f766e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
            </div>
            <h1 style="color: #0f766e; font-size: 28px; margin-bottom: 16px; font-weight: 700;">Welcome to {settings.APP_NAME}!</h1>
            <p style="font-size: 16px; color: #4b5563; margin-bottom: 32px; line-height: 1.6; max-width: 480px; margin-left: auto; margin-right: auto;">
                Hi <b>{name}</b>,<br><br>
                We're thrilled to have you! Your account has been successfully verified and created. 
                You can now easily book top-tier physiotherapy sessions, manage your health records, and connect with our certified professionals.
            </p>
            <a href="{settings.FRONTEND_URL}" style="display: inline-block; background-color: #0f766e; color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px -1px rgba(15, 118, 110, 0.2);">
                Explore Your Dashboard
            </a>
            <p style="font-size: 14px; color: #6b7280; margin-top: 48px;">
                If you have any questions or need assistance, feel free to reply directly to this email. Our support team is always here for you.
            </p>
        </div>
        """
        return await self.send(to, f"Welcome to {settings.APP_NAME} 🎉", body)

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

    async def send_verification_otp(self, to: str, otp: str) -> bool:
        body = (
            "<p>Welcome to Home Physio India!</p>"
            "<p>Please use the following 6-digit OTP to verify your email address. This code is valid for 10 minutes.</p>"
            f'<div style="text-align:center;margin:30px 0;">'
            f'<span style="font-size:32px;font-weight:bold;letter-spacing:8px;background:#f3f4f6;padding:12px 24px;border-radius:8px;color:#111;">{otp}</span>'
            f'</div>'
            "<p>If you did not sign up for an account, you can safely ignore this email.</p>"
        )
        text_fallback = f"Your email verification OTP is {otp}. It is valid for 10 minutes."
        return await self.send(to, "Verify Your Email", body, text_fallback)

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
