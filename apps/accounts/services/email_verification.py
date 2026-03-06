"""
apps/accounts/services/email_verification.py

Resend-powered email service for Fyndars.

HTML is built by apps.core.email_templates — this file only
handles the sending logic and public API.

Sends:
  - Email verification (OTP code + magic link)
  - Welcome email after successful verification
"""
import logging
import resend

from django.conf import settings
from apps.core.email_templates import build_email

log = logging.getLogger(__name__)

# Add this temporary line at the top of send_verification_email in email_verification.py

resend.api_key = settings.RESEND_API_KEY

# Using Resend's shared domain until fyndars.com is verified at resend.com/domains.
# Once verified, change to: "Fyndars <noreply@fyndars.com>"
FROM_ADDRESS = "Fyndars <onboarding@resend.dev>"
FRONTEND_URL = getattr(settings, "FRONTEND_URL", "http://localhost:3000")


def send_verification_email(user, otp: str, token: str) -> bool:
    """
    Send the OTP + magic-link verification email.
    Returns True on success, False on failure (never raises).
    """
    log.info("FROM_ADDRESS in use: %s", FROM_ADDRESS)

    user_name  = user.get_full_name_or_email()
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"

    try:
        resend.Emails.send({
            "from":    FROM_ADDRESS,
            "to":      [user.email],
            "subject": "Verify your Fyndars account",
            "html":    build_email(
                variant="verification",
                user_name=user_name,
                otp=otp,
                verify_url=verify_url,
            ),
        })
        log.info("Verification email sent to %s", user.email)
        return True
    except Exception as exc:
        log.error("Failed to send verification email to %s: %s", user.email, exc)
        return False


def send_welcome_email(user) -> bool:
    """
    Send the welcome email after successful verification.
    Returns True on success, False on failure (never raises).
    """
    user_name = user.get_full_name_or_email()

    try:
        resend.Emails.send({
            "from":    FROM_ADDRESS,
            "to":      [user.email],
            "subject": "Welcome to Fyndars 🏠",
            "html":    build_email(
                variant="welcome",
                user_name=user_name,
            ),
        })
        log.info("Welcome email sent to %s", user.email)
        return True
    except Exception as exc:
        log.error("Failed to send welcome email to %s: %s", user.email, exc)
        return False