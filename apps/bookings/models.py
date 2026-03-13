# apps/bookings/models.py
import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class EmergencyType(models.TextChoices):
    ACCIDENT    = "accident",    "Accident / Trauma"
    CARDIAC     = "cardiac",     "Cardiac Emergency"
    MATERNITY   = "maternity",   "Maternity"
    RESPIRATORY = "respiratory", "Respiratory"
    STROKE      = "stroke",      "Stroke"
    PAEDIATRIC  = "paediatric",  "Paediatric"
    OTHER       = "other",       "Other"


class BookingStatus(models.TextChoices):
    PENDING    = "pending",    "Pending"
    CONFIRMED  = "confirmed",  "Confirmed"
    DISPATCHED = "dispatched", "Dispatched"
    ONGOING    = "ongoing",    "Ongoing / En Route"
    ARRIVED    = "arrived",    "Arrived at Scene"
    COMPLETED  = "completed",  "Completed"
    CANCELLED  = "cancelled",  "Cancelled"


class PaymentStatus(models.TextChoices):
    UNPAID  = "unpaid",  "Unpaid"
    PAID    = "paid",    "Paid"
    PARTIAL = "partial", "Partially Paid"
    WAIVED  = "waived",  "Waived"


class PaymentMethod(models.TextChoices):
    CASH         = "cash",         "Cash on Arrival"
    MTN_MONEY    = "mtn_money",    "MTN Mobile Money"
    AIRTEL_MONEY = "airtel_money", "Airtel Money"
    INSURANCE    = "insurance",    "Insurance"


# Valid state machine transitions
VALID_STATUS_TRANSITIONS = {
    BookingStatus.PENDING:    {BookingStatus.CONFIRMED, BookingStatus.CANCELLED},
    BookingStatus.CONFIRMED:  {BookingStatus.DISPATCHED, BookingStatus.CANCELLED},
    BookingStatus.DISPATCHED: {BookingStatus.ONGOING, BookingStatus.CANCELLED},
    BookingStatus.ONGOING:    {BookingStatus.ARRIVED, BookingStatus.CANCELLED},
    BookingStatus.ARRIVED:    {BookingStatus.COMPLETED, BookingStatus.CANCELLED},
    BookingStatus.COMPLETED:  set(),
    BookingStatus.CANCELLED:  set(),
}


class BookingManager(models.Manager):
    def active(self):
        return self.exclude(status__in=[BookingStatus.COMPLETED, BookingStatus.CANCELLED])

    def for_client(self, user):
        return self.filter(client=user)

    def pending(self):
        return self.filter(status=BookingStatus.PENDING)


class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Human-readable reference e.g. ML-0047
    reference = models.CharField(max_length=20, unique=True, editable=False, db_index=True)

    # Who booked (nullable for walk-in / operator-created bookings)
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bookings",
    )

    # Patient info (may differ from client)
    patient_name  = models.CharField(max_length=200)
    patient_phone = models.CharField(max_length=20)
    patient_age   = models.PositiveSmallIntegerField(null=True, blank=True)

    emergency_type = models.CharField(
        max_length=20, choices=EmergencyType.choices, default=EmergencyType.OTHER, db_index=True
    )
    notes = models.TextField(blank=True, default="")

    # Pickup location
    pickup_address = models.TextField()
    pickup_lat     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_lon     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Optional destination (some emergencies have a pre-specified hospital)
    destination_address = models.TextField(blank=True, default="")
    destination_lat     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_lon     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Assigned resources
    ambulance = models.ForeignKey(
        "ambulances.Ambulance",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bookings",
    )
    hospital = models.ForeignKey(
        "hospitals.Hospital",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bookings",
    )

    # Status
    status = models.CharField(
        max_length=15, choices=BookingStatus.choices, default=BookingStatus.PENDING, db_index=True
    )
    cancellation_reason = models.TextField(blank=True, default="")

    # Payment
    payment_method = models.CharField(
        max_length=15, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID, db_index=True
    )
    insurance_provider   = models.CharField(max_length=200, blank=True, default="")
    insurance_policy_ref = models.CharField(max_length=100, blank=True, default="")

    # Fare (stored in smallest currency unit, e.g. UGX)
    base_fare    = models.PositiveIntegerField(default=0)
    platform_fee = models.PositiveIntegerField(default=5000)
    discount     = models.PositiveIntegerField(default=0, help_text="Discount amount in UGX")
    total_fare   = models.PositiveIntegerField(default=0)

    # Status timestamps
    created_at    = models.DateTimeField(auto_now_add=True, db_index=True)
    confirmed_at  = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    ongoing_at    = models.DateTimeField(null=True, blank=True)
    arrived_at    = models.DateTimeField(null=True, blank=True)
    completed_at  = models.DateTimeField(null=True, blank=True)
    cancelled_at  = models.DateTimeField(null=True, blank=True)
    updated_at    = models.DateTimeField(auto_now=True)

    # Soft delete
    is_deleted = models.BooleanField(default=False, db_index=True)

    objects = BookingManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["client", "status"]),
        ]

    def __str__(self):
        return f"{self.reference} — {self.patient_name} [{self.get_status_display()}]"

    # ------------------------------------------------------------------
    # Reference generation (race-condition-safe)
    # ------------------------------------------------------------------
    @classmethod
    def _generate_reference(cls) -> str:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM bookings_booking"
            )
            count = cursor.fetchone()[0]
        return f"ML-{count + 1:04d}"

    # ------------------------------------------------------------------
    # Fare helpers
    # ------------------------------------------------------------------
    def calculate_total_fare(self) -> int:
        return max(0, self.base_fare + self.platform_fee - self.discount)

    # ------------------------------------------------------------------
    # Status machine
    # ------------------------------------------------------------------
    def can_transition_to(self, new_status: str) -> bool:
        return new_status in VALID_STATUS_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: str, save: bool = True) -> None:
        if not self.can_transition_to(new_status):
            raise ValidationError(
                f"Cannot move booking from '{self.status}' to '{new_status}'."
            )
        now = timezone.now()
        self.status = new_status
        timestamp_map = {
            BookingStatus.CONFIRMED:  "confirmed_at",
            BookingStatus.DISPATCHED: "dispatched_at",
            BookingStatus.ONGOING:    "ongoing_at",
            BookingStatus.ARRIVED:    "arrived_at",
            BookingStatus.COMPLETED:  "completed_at",
            BookingStatus.CANCELLED:  "cancelled_at",
        }
        if field := timestamp_map.get(new_status):
            setattr(self, field, now)
        if save:
            self.save()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self.status not in {BookingStatus.COMPLETED, BookingStatus.CANCELLED}

    @property
    def duration_minutes(self) -> int | None:
        """Minutes from dispatch to completion, if available."""
        if self.dispatched_at and self.completed_at:
            delta = self.completed_at - self.dispatched_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def has_gps(self) -> bool:
        return self.pickup_lat is not None and self.pickup_lon is not None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def clean(self):
        if self.payment_method == PaymentMethod.INSURANCE:
            if not self.insurance_provider:
                raise ValidationError({"insurance_provider": "Required when payment method is Insurance."})
        if self.discount > (self.base_fare + self.platform_fee):
            raise ValidationError({"discount": "Discount cannot exceed total charges."})

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()
        self.total_fare = self.calculate_total_fare()
        self.full_clean()
        super().save(*args, **kwargs)


class BookingStatusLog(models.Model):
    """Immutable audit trail for every status change."""
    booking    = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="status_logs")
    from_status = models.CharField(max_length=15, choices=BookingStatus.choices, blank=True, default="")
    to_status  = models.CharField(max_length=15, choices=BookingStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    note       = models.TextField(blank=True, default="")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.booking.reference}: {self.from_status} → {self.to_status}"