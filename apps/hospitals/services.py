# apps/hospitals/services.py
from __future__ import annotations

from django.db import transaction
from django.db.models import QuerySet, Q
from django.core.exceptions import ValidationError

from .models import Hospital, HospitalReview, HospitalStatus, Speciality


class HospitalService:

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def create_hospital(admin_user, validated_data: dict) -> Hospital:
        hospital = Hospital(admin_user=admin_user, **validated_data)
        hospital.full_clean()
        hospital.save()
        return hospital

    @staticmethod
    @transaction.atomic
    def update_hospital(hospital: Hospital, validated_data: dict) -> Hospital:
        for field, value in validated_data.items():
            setattr(hospital, field, value)
        hospital.full_clean()
        hospital.save()
        return hospital

    # ------------------------------------------------------------------
    # Platform operations (staff)
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def verify(hospital: Hospital) -> Hospital:
        hospital.is_verified = True
        hospital.save(update_fields=["is_verified", "updated_at"])
        return hospital

    @staticmethod
    @transaction.atomic
    def deactivate(hospital: Hospital) -> Hospital:
        hospital.is_active = False
        hospital.status = HospitalStatus.INACTIVE
        hospital.save(update_fields=["is_active", "status", "updated_at"])
        return hospital

    @staticmethod
    @transaction.atomic
    def set_featured(hospital: Hospital, featured: bool) -> Hospital:
        hospital.is_featured = featured
        hospital.save(update_fields=["is_featured", "updated_at"])
        return hospital

    # ------------------------------------------------------------------
    # Hospital-admin operations
    # ------------------------------------------------------------------
    @staticmethod
    def update_bed_count(hospital: Hospital, total: int, available: int) -> Hospital:
        if available > total:
            raise ValidationError("Available beds cannot exceed total beds.")
        hospital.total_beds     = total
        hospital.available_beds = available
        # Auto-set status based on capacity
        if available == 0:
            hospital.status = HospitalStatus.FULL
        elif hospital.status == HospitalStatus.FULL:
            hospital.status = HospitalStatus.ACTIVE
        hospital.save(update_fields=["total_beds", "available_beds", "status", "updated_at"])
        return hospital

    @staticmethod
    def set_status(hospital: Hospital, new_status: str) -> Hospital:
        hospital.status = new_status
        hospital.save(update_fields=["status", "updated_at"])
        return hospital

    # ------------------------------------------------------------------
    # Client-facing queries
    # ------------------------------------------------------------------
    @staticmethod
    def search(
        district: str | None = None,
        speciality: str | None = None,
        hospital_type: str | None = None,
        accepting_only: bool = True,
        query: str | None = None,
        is_24_hours: bool | None = None,
        has_icu: bool | None = None,
        accepts_insurance: bool | None = None,
    ) -> QuerySet[Hospital]:
        qs = Hospital.objects.filter(is_verified=True, is_active=True)

        if accepting_only:
            qs = qs.filter(
                status__in=[HospitalStatus.ACTIVE, HospitalStatus.EMERGENCY_ONLY],
                available_beds__gt=0,
            )
        if district:
            qs = qs.filter(district__iexact=district)
        if hospital_type:
            qs = qs.filter(hospital_type=hospital_type)
        if speciality:
            # JSONField contains lookup
            qs = qs.filter(specialities__contains=speciality)
        if query:
            qs = qs.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(address__icontains=query)
            )
        if is_24_hours is not None:
            qs = qs.filter(is_24_hours=is_24_hours)
        if has_icu is not None:
            qs = qs.filter(has_icu=has_icu)
        if accepts_insurance is not None:
            qs = qs.filter(accepts_insurance=accepts_insurance)

        return qs.order_by("-is_featured", "-rating", "name")

    @staticmethod
    def get_for_emergency(emergency_type: str) -> QuerySet[Hospital]:
        """Return hospitals suited to a given emergency type, ranked by rating."""
        # Map booking emergency types → hospital specialities
        EMERGENCY_MAP = {
            "cardiac":     Speciality.CARDIAC,
            "maternity":   Speciality.MATERNITY,
            "paediatric":  Speciality.PAEDIATRIC,
            "stroke":      Speciality.NEUROLOGY,
            "accident":    Speciality.TRAUMA,
            "respiratory": Speciality.ICU,
        }
        speciality = EMERGENCY_MAP.get(emergency_type)
        qs = Hospital.objects.filter(
            is_verified=True, is_active=True,
            status__in=[HospitalStatus.ACTIVE, HospitalStatus.EMERGENCY_ONLY],
        )
        if speciality:
            qs = qs.filter(specialities__contains=speciality)
        return qs.order_by("-is_featured", "-rating")


class ReviewService:

    @staticmethod
    @transaction.atomic
    def submit_review(reviewer, hospital: Hospital, booking, rating: int, comment: str = "") -> HospitalReview:
        from bookings.models import BookingStatus
        if booking.hospital != hospital:
            raise ValidationError("This booking was not associated with the selected hospital.")
        if booking.status != BookingStatus.COMPLETED:
            raise ValidationError("You can only review a completed booking.")
        if booking.client != reviewer:
            raise ValidationError("You can only review your own bookings.")
        review = HospitalReview.objects.create(
            hospital=hospital,
            reviewer=reviewer,
            booking=booking,
            rating=rating,
            comment=comment,
            is_approved=False,
        )
        return review

    @staticmethod
    @transaction.atomic
    def approve_review(review: HospitalReview) -> HospitalReview:
        review.is_approved = True
        review.save(update_fields=["is_approved"])
        review.hospital.refresh_aggregate_rating()
        return review

    @staticmethod
    @transaction.atomic
    def reject_review(review: HospitalReview) -> None:
        hospital = review.hospital
        review.delete()
        hospital.refresh_aggregate_rating()