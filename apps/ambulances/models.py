# apps/ambulances/models.py
import uuid
from django.db import models
from django.conf import settings


class AmbulanceType(models.TextChoices):
    BLS      = "BLS",     "Basic Life Support"
    ALS      = "ALS",     "Advanced Life Support"
    ICU      = "ICU",     "ICU-Equipped"
    MATERNITY= "MAT",     "Maternity"
    NEONATAL = "NEO",     "Neonatal"
    OFFROAD  = "OFF",     "Off-Road ALS"


class AmbulanceStatus(models.TextChoices):
    AVAILABLE   = "available",   "Available"
    BUSY        = "busy",        "Busy / On Call"
    MAINTENANCE = "maintenance", "Under Maintenance"
    OFFLINE     = "offline",     "Offline"


#  Provider (organisation that owns ambulances) 

class Provider(models.Model):
    """Maps 1-to-1 to a ProviderAdminProfile user."""
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_user   = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="provider",
        limit_choices_to={"role": "provider_admin"},
    )
    name         = models.CharField(max_length=150)
    description  = models.TextField(blank=True, null=True)
    phone        = models.CharField(max_length=20, blank=True, null=True)
    address      = models.TextField(blank=True, null=True)
    district     = models.CharField(max_length=100, default="Kampala")
    is_verified  = models.BooleanField(default=False, db_index=True)
    is_active    = models.BooleanField(default=True,  db_index=True)
    rating       = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


#  Ambulance (vehicle in a provider's fleet) 

class Ambulance(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider      = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="ambulances")
    plate_number  = models.CharField(max_length=20, unique=True)
    vehicle_make  = models.CharField(max_length=100, blank=True, null=True)
    vehicle_model = models.CharField(max_length=100, blank=True, null=True)
    vehicle_year  = models.PositiveSmallIntegerField(null=True, blank=True)
    ambulance_type= models.CharField(max_length=5, choices=AmbulanceType.choices, default=AmbulanceType.BLS)
    status        = models.CharField(max_length=15, choices=AmbulanceStatus.choices, default=AmbulanceStatus.AVAILABLE, db_index=True)

    # Location (updated when driver checks in)
    latitude      = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Assigned driver (optional)
    driver        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="assigned_ambulance",
        limit_choices_to={"role": "driver"},
    )

    base_fare     = models.PositiveIntegerField(default=100000, help_text="UGX")
    is_active     = models.BooleanField(default=True, db_index=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "plate_number"]

    def __str__(self):
        return f"{self.plate_number} ({self.provider.name})"

    @property
    def is_available(self):
        return self.status == AmbulanceStatus.AVAILABLE