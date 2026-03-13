# apps/ambulances/services.py
from __future__ import annotations

from django.db import transaction
from django.db.models import QuerySet
from django.core.exceptions import ValidationError

from .models import Ambulance, AmbulanceStatus, Provider


class ProviderService:

    @staticmethod
    @transaction.atomic
    def create_provider(admin_user, validated_data: dict) -> Provider:
        provider = Provider(admin_user=admin_user, **validated_data)
        provider.full_clean()
        provider.save()
        return provider

    @staticmethod
    @transaction.atomic
    def verify_provider(provider: Provider, verified_by) -> Provider:
        provider.is_verified = True
        provider.save(update_fields=["is_verified"])
        return provider

    @staticmethod
    @transaction.atomic
    def deactivate_provider(provider: Provider) -> Provider:
        provider.is_active = False
        provider.ambulances.filter(is_active=True).update(
            is_active=False, status=AmbulanceStatus.OFFLINE
        )
        provider.save(update_fields=["is_active"])
        return provider

    @staticmethod
    def get_verified_active() -> QuerySet[Provider]:
        return Provider.objects.filter(is_verified=True, is_active=True)


class AmbulanceService:

    @staticmethod
    @transaction.atomic
    def create_ambulance(provider: Provider, validated_data: dict) -> Ambulance:
        ambulance = Ambulance(provider=provider, **validated_data)
        ambulance.full_clean()
        ambulance.save()
        return ambulance

    @staticmethod
    def set_status(ambulance: Ambulance, new_status: str, save: bool = True) -> Ambulance:
        allowed = set(AmbulanceStatus.values)
        if new_status not in allowed:
            raise ValidationError(f"Invalid status '{new_status}'.")
        ambulance.status = new_status
        if save:
            ambulance.save(update_fields=["status", "updated_at"])
        return ambulance

    @staticmethod
    def update_location(ambulance: Ambulance, lat: float, lon: float) -> Ambulance:
        ambulance.latitude = lat
        ambulance.longitude = lon
        ambulance.save(update_fields=["latitude", "longitude", "updated_at"])
        return ambulance

    @staticmethod
    def assign_driver(ambulance: Ambulance, driver) -> Ambulance:
        ambulance.driver = driver
        ambulance.save(update_fields=["driver", "updated_at"])
        return ambulance

    @staticmethod
    def unassign_driver(ambulance: Ambulance) -> Ambulance:
        ambulance.driver = None
        ambulance.save(update_fields=["driver", "updated_at"])
        return ambulance

    @staticmethod
    def get_available(provider: Provider | None = None) -> QuerySet[Ambulance]:
        qs = Ambulance.objects.filter(
            is_active=True, status=AmbulanceStatus.AVAILABLE
        ).select_related("provider", "driver")
        if provider:
            qs = qs.filter(provider=provider)
        return qs

    @staticmethod
    def get_for_provider(provider: Provider) -> QuerySet[Ambulance]:
        return Ambulance.objects.filter(
            provider=provider
        ).select_related("driver")