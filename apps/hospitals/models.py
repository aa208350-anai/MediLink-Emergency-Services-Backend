# apps/hospitals/models.py
import uuid
from django.db import models
from django.conf import settings


class HospitalType(models.TextChoices):
    PUBLIC      = "public",      "Public / Government"
    PRIVATE     = "private",     "Private"
    NGO         = "ngo",         "NGO / Mission"
    CLINIC      = "clinic",      "Clinic"
    SPECIALISED = "specialised", "Specialised Centre"


class HospitalStatus(models.TextChoices):
    ACTIVE      = "active",      "Active"
    INACTIVE    = "inactive",    "Inactive"
    FULL        = "full",        "At Capacity"
    EMERGENCY_ONLY = "emergency_only", "Emergency Cases Only"


class Speciality(models.TextChoices):
    GENERAL     = "general",     "General Medicine"
    TRAUMA      = "trauma",      "Trauma & Emergency"
    CARDIAC     = "cardiac",     "Cardiology"
    MATERNITY   = "maternity",   "Maternity & Obstetrics"
    PAEDIATRIC  = "paediatric",  "Paediatrics"
    NEUROLOGY   = "neurology",   "Neurology"
    ORTHOPAEDIC = "orthopaedic", "Orthopaedics"
    ONCOLOGY    = "oncology",    "Oncology"
    ICU         = "icu",         "Intensive Care"
    BURNS       = "burns",       "Burns Unit"


class Hospital(models.Model):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Admin contact
    admin_user      = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="hospital",
        limit_choices_to={"role": "hospital_admin"},
    )

    # Identity
    name            = models.CharField(max_length=200, db_index=True)
    hospital_type   = models.CharField(max_length=15, choices=HospitalType.choices, default=HospitalType.PRIVATE)
    registration_no = models.CharField(max_length=100, unique=True, blank=True, default="")
    description     = models.TextField(blank=True, default="")

    # Contact
    phone_primary   = models.CharField(max_length=20)
    phone_emergency = models.CharField(max_length=20, blank=True, default="")
    email           = models.EmailField(blank=True, default="")
    website         = models.URLField(blank=True, default="")

    # Location
    address         = models.TextField()
    district        = models.CharField(max_length=100, default="Kampala", db_index=True)
    latitude        = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude       = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Capabilities
    specialities    = models.JSONField(default=list, blank=True,
                                       help_text="List of Speciality values this hospital offers.")
    has_icu         = models.BooleanField(default=False)
    has_maternity   = models.BooleanField(default=False)
    has_blood_bank  = models.BooleanField(default=False)
    has_ambulance   = models.BooleanField(default=False, help_text="Hospital operates own ambulances.")
    accepts_insurance = models.BooleanField(default=False)
    is_24_hours     = models.BooleanField(default=False)

    # Bed availability (updated by hospital admin)
    total_beds      = models.PositiveSmallIntegerField(default=0)
    available_beds  = models.PositiveSmallIntegerField(default=0)

    # Platform flags
    status          = models.CharField(max_length=20, choices=HospitalStatus.choices,
                                       default=HospitalStatus.ACTIVE, db_index=True)
    is_verified     = models.BooleanField(default=False, db_index=True)
    is_active       = models.BooleanField(default=True, db_index=True)
    is_featured     = models.BooleanField(default=False, db_index=True,
                                          help_text="Pinned at top of client search results.")

    # Rating (aggregated from reviews)
    rating          = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count    = models.PositiveIntegerField(default=0)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-rating", "name"]
        indexes  = [
            models.Index(fields=["district", "status"]),
            models.Index(fields=["is_verified", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_hospital_type_display()})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.available_beds > self.total_beds:
            raise ValidationError({"available_beds": "Cannot exceed total beds."})
        # Validate specialities list contains valid choices
        valid = {s.value for s in Speciality}
        invalid = [s for s in (self.specialities or []) if s not in valid]
        if invalid:
            raise ValidationError({"specialities": f"Invalid specialities: {invalid}"})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def has_gps(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def bed_occupancy_pct(self) -> float | None:
        if self.total_beds == 0:
            return None
        return round((1 - self.available_beds / self.total_beds) * 100, 1)

    @property
    def is_accepting_patients(self) -> bool:
        return (
            self.is_active
            and self.is_verified
            and self.status in {HospitalStatus.ACTIVE, HospitalStatus.EMERGENCY_ONLY}
            and self.available_beds > 0
        )


class HospitalReview(models.Model):
    """Client review left after a completed booking."""
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hospital    = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="reviews")
    reviewer    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="hospital_reviews",
    )
    # Link review to a specific booking to prevent duplicates
    booking     = models.OneToOneField(
        "bookings.Booking", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="hospital_review",
    )
    rating      = models.PositiveSmallIntegerField(help_text="1–5 stars")
    comment     = models.TextField(blank=True, default="")
    is_approved = models.BooleanField(default=False, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.hospital.name} — {self.rating}★ by {self.reviewer}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not (1 <= self.rating <= 5):
            raise ValidationError({"rating": "Rating must be between 1 and 5."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        # Recalculate hospital aggregate rating on every save
        self.hospital.refresh_aggregate_rating()

    def delete(self, *args, **kwargs):
        hospital = self.hospital
        super().delete(*args, **kwargs)
        hospital.refresh_aggregate_rating()


# Attach aggregate helper to Hospital without circular import
def _refresh_aggregate_rating(self):
    from django.db.models import Avg, Count
    agg = self.reviews.filter(is_approved=True).aggregate(
        avg=Avg("rating"), count=Count("id")
    )
    self.rating       = round(agg["avg"] or 0, 2)
    self.review_count = agg["count"] or 0
    self.save(update_fields=["rating", "review_count"])


Hospital.refresh_aggregate_rating = _refresh_aggregate_rating