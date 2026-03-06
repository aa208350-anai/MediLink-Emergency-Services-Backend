# apps/accounts/models/email_verification.py
import random
import string
import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.conf import settings


def _default_expires():
    return timezone.now() + timedelta(minutes=30)


def _generate_otp():
    """6-digit numeric OTP."""
    return "".join(random.choices(string.digits, k=6))


def _generate_token():
    """URL-safe token for magic-link verification."""
    return uuid.uuid4().hex


class EmailVerification(models.Model):
    """
    Stores a one-time verification code (OTP) and a magic-link token
    for a given user email.  Only one active record per user at a time
    — old ones are deleted on issue.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verifications",
    )
    email      = models.EmailField()          # snapshot — user may change email later
    otp        = models.CharField(max_length=6,  default=_generate_otp)
    token      = models.CharField(max_length=32, default=_generate_token, unique=True)
    is_used    = models.BooleanField(default=False)
    expires_at = models.DateTimeField(default=_default_expires)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Email Verification"

    def __str__(self):
        return f"Verification for {self.email} ({'used' if self.is_used else 'pending'})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    def consume(self):
        """Mark as used and activate the user's email."""
        self.is_used = True
        self.save(update_fields=["is_used"])
        # Mark the user's account as email-verified
        user = self.user
        user.is_active = True
        user.save(update_fields=["is_active"])