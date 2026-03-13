from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import uuid

from apps.accounts.managers.custom_user_manager import CustomUserManager
from apps.accounts.models.constants import AccountType


class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, validators=[validate_email])
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    role = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.CLIENT,
    )

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "custom_user"
        ordering = ["created_at"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.get_full_name_or_email()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_full_name(self):
        return self.full_name

    def get_full_name_or_email(self):
        full_name = self.full_name.strip()
        return full_name if full_name else self.email or f"User {str(self.id)[:8]}"

    # Role helpers
    @property
    def is_admin(self):
        return self.role == AccountType.ADMIN or self.is_superuser

    @property
    def is_driver(self):
        return self.role == AccountType.DRIVER

    @property
    def is_client(self):
        return self.role == AccountType.CLIENT

    @property
    def is_staff_member(self):
        return self.role == AccountType.STAFF
    
    @property
    def is_provider_admin(self):
        return self.role == AccountType.PROVIDER_ADMIN

    # Friendly email validation
    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.lower().strip()
            if CustomUser.objects.exclude(pk=self.pk).filter(email=self.email).exists():
                raise ValidationError({
                    "email": "A user with this email address already exists."
                })