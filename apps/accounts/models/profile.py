# apps/accounts/models/profiles.py

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import RegexValidator
from cloudinary.models import CloudinaryField


# =====================================================
# SHARED MIXINS
# =====================================================

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class VerificationMixin(models.Model):
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_verified",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def verify(self, verified_by):
        self.is_verified = True
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        self.save(update_fields=["is_verified", "verified_by", "verified_at"])


class BaseProfile(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    profile_photo = CloudinaryField("profile_photo", folder="profiles", blank=True, null=True)

    phone_validator = RegexValidator(
        r'^\+?\d{9,15}$',
        "Enter a valid phone number."
    )
    phone = models.CharField(max_length=20, blank=True, null=True, validators=[phone_validator])

    class Meta:
        abstract = True

    def __str__(self):
        return self.user.get_full_name_or_email()


# =====================================================
# CLIENT PROFILE
# =====================================================

class ClientProfile(BaseProfile):
    """Profile for end-users who book rides/services."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "client"},
        related_name="client_profile",
    )

    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    additional_notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "client profile"


# =====================================================
# DRIVER PROFILE
# =====================================================

class DriverProfile(BaseProfile, VerificationMixin):
    """Profile for drivers who fulfil service requests."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "driver"},
        related_name="driver_profile",
    )

    # Identity / licensing
    national_id_front = CloudinaryField("id_front", folder="driver_docs", blank=True, null=True)
    national_id_back  = CloudinaryField("id_back",  folder="driver_docs", blank=True, null=True)
    license_number      = models.CharField(max_length=50, blank=True, null=True)
    license_expiry_date = models.DateField(null=True, blank=True)

    # Vehicle
    vehicle_make        = models.CharField(max_length=100, blank=True, null=True)
    vehicle_model       = models.CharField(max_length=100, blank=True, null=True)
    vehicle_year        = models.PositiveSmallIntegerField(null=True, blank=True)
    vehicle_plate       = models.CharField(max_length=20, blank=True, null=True)
    vehicle_color       = models.CharField(max_length=50, blank=True, null=True)

    # Availability & metrics
    is_available    = models.BooleanField(default=False, db_index=True)
    average_rating  = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, editable=False)
    total_reviews   = models.PositiveIntegerField(default=0, editable=False)
    total_trips     = models.PositiveIntegerField(default=0, editable=False)

    # Contact
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = "driver profile"
        indexes = [
            models.Index(fields=["is_verified"]),
            models.Index(fields=["is_available"]),
            models.Index(fields=["average_rating"]),
        ]


# =====================================================
# STAFF PROFILE
# =====================================================

class StaffProfile(BaseProfile):
    """Profile for internal staff / operators."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "staff"},
        related_name="staff_profile",
    )

    department  = models.CharField(max_length=100, blank=True, null=True)
    job_title   = models.CharField(max_length=100, blank=True, null=True)
    employee_id = models.CharField(max_length=50,  blank=True, null=True, unique=True)

    class Meta:
        verbose_name = "staff profile"


# =====================================================
# PROVIDER ADMIN PROFILE
# =====================================================

class ProviderAdminProfile(BaseProfile, VerificationMixin):
    """Profile for the admin of a service-provider organisation."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "provider_admin"},
        related_name="provider_admin_profile",
    )

    # Organisation
    company_name                = models.CharField(max_length=150, blank=True, null=True)
    company_registration_number = models.CharField(max_length=50,  blank=True, null=True)
    company_logo                = CloudinaryField("company_logo", folder="provider_logos", blank=True, null=True)
    company_website             = models.URLField(blank=True, null=True)
    office_address              = models.TextField(blank=True, null=True)
    office_phone                = models.CharField(max_length=20, blank=True, null=True)
    tin_number                  = models.CharField(max_length=20, blank=True, null=True)

    # Social
    whatsapp_number  = models.CharField(max_length=20, blank=True, null=True)
    facebook_page    = models.URLField(blank=True, null=True)
    instagram_handle = models.CharField(max_length=50, blank=True, null=True)

    # Metrics
    average_rating     = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, editable=False)
    total_reviews      = models.PositiveIntegerField(default=0, editable=False)
    total_transactions = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        verbose_name = "provider admin profile"
        indexes = [
            models.Index(fields=["is_verified"]),
            models.Index(fields=["average_rating"]),
        ]


# =====================================================
# ADMIN PROFILE
# =====================================================

class AdminProfile(BaseProfile):
    """Profile for platform super-admins."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "admin"},
        related_name="admin_profile",
    )

    can_create_users     = models.BooleanField(default=False)
    can_verify_profiles  = models.BooleanField(default=False)
    can_manage_drivers   = models.BooleanField(default=True)
    can_manage_providers = models.BooleanField(default=False)
    can_manage_payments  = models.BooleanField(default=False)
    can_manage_staff     = models.BooleanField(default=False)

    class Meta:
        verbose_name = "admin profile"