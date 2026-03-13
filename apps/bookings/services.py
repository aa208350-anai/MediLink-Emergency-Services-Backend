# apps/bookings/services.py
from __future__ import annotations

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Booking, BookingStatus, BookingStatusLog


class BookingService:
    """
    Central service layer for all booking business logic.
    All mutations go through here — views/serializers stay thin.
    """

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def create_booking(client, validated_data: dict) -> Booking:
        """Create a new booking and record the initial status log."""
        booking = Booking(client=client, **validated_data)
        booking.full_clean()
        booking.save()

        BookingStatusLog.objects.create(
            booking=booking,
            from_status="",
            to_status=BookingStatus.PENDING,
            changed_by=client,
            note="Booking created.",
        )
        return booking

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def transition(
        booking: Booking,
        new_status: str,
        changed_by=None,
        note: str = "",
        extra_fields: dict | None = None,
    ) -> Booking:
        """
        Transition a booking to a new status.
        `extra_fields` allows callers to set e.g. ambulance, cancellation_reason
        in the same atomic operation.
        """
        if not booking.can_transition_to(new_status):
            raise ValidationError(
                f"Cannot move booking '{booking.reference}' "
                f"from '{booking.status}' to '{new_status}'."
            )

        previous = booking.status

        if extra_fields:
            for field, value in extra_fields.items():
                setattr(booking, field, value)

        booking.transition_to(new_status, save=False)
        booking.save()

        BookingStatusLog.objects.create(
            booking=booking,
            from_status=previous,
            to_status=new_status,
            changed_by=changed_by,
            note=note,
        )
        return booking

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------
    @classmethod
    def confirm(cls, booking: Booking, operator, ambulance=None) -> Booking:
        extra = {}
        if ambulance:
            extra["ambulance"] = ambulance
        return cls.transition(
            booking, BookingStatus.CONFIRMED, changed_by=operator,
            note="Booking confirmed by operator.", extra_fields=extra or None,
        )

    @classmethod
    def dispatch(cls, booking: Booking, operator, ambulance=None) -> Booking:
        if ambulance is None and booking.ambulance is None:
            raise ValidationError("An ambulance must be assigned before dispatch.")
        extra = {"ambulance": ambulance} if ambulance else None
        return cls.transition(
            booking, BookingStatus.DISPATCHED, changed_by=operator,
            note="Ambulance dispatched.", extra_fields=extra,
        )

    @classmethod
    def mark_ongoing(cls, booking: Booking, driver) -> Booking:
        return cls.transition(
            booking, BookingStatus.ONGOING, changed_by=driver,
            note="En route to scene.",
        )

    @classmethod
    def mark_arrived(cls, booking: Booking, driver) -> Booking:
        return cls.transition(
            booking, BookingStatus.ARRIVED, changed_by=driver,
            note="Arrived at scene.",
        )

    @classmethod
    def complete(cls, booking: Booking, operator, note: str = "") -> Booking:
        return cls.transition(
            booking, BookingStatus.COMPLETED, changed_by=operator,
            note=note or "Booking completed.",
        )

    @classmethod
    def cancel(cls, booking: Booking, cancelled_by, reason: str = "") -> Booking:
        return cls.transition(
            booking, BookingStatus.CANCELLED, changed_by=cancelled_by,
            note=reason or "Booking cancelled.",
            extra_fields={"cancellation_reason": reason},
        )

    # ------------------------------------------------------------------
    # Fare utilities
    # ------------------------------------------------------------------
    @staticmethod
    def update_fare(booking: Booking, base_fare: int, platform_fee: int = None, discount: int = 0) -> Booking:
        if not booking.is_active:
            raise ValidationError("Cannot update fare on a closed booking.")
        booking.base_fare = base_fare
        if platform_fee is not None:
            booking.platform_fee = platform_fee
        booking.discount = discount
        booking.total_fare = booking.calculate_total_fare()
        booking.save(update_fields=["base_fare", "platform_fee", "discount", "total_fare", "updated_at"])
        return booking

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @staticmethod
    def get_active_for_client(user) -> "QuerySet[Booking]":
        return Booking.objects.for_client(user).active().select_related("ambulance", "hospital")

    @staticmethod
    def get_history_for_client(user) -> "QuerySet[Booking]":
        return (
            Booking.objects.for_client(user)
            .filter(status__in=[BookingStatus.COMPLETED, BookingStatus.CANCELLED])
            .select_related("ambulance", "hospital")
        )