# apps/bookings/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Booking, BookingStatusLog, BookingStatus, PaymentMethod

User = get_user_model()


# ------------------------------------------------------------------
# Nested / read-only helpers
# ------------------------------------------------------------------
class ClientSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "email"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email


class BookingStatusLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BookingStatusLog
        fields = [
            "id", "from_status", "to_status",
            "changed_by_name", "note", "changed_at",
        ]

    def get_changed_by_name(self, obj):
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.email
        return None


# ------------------------------------------------------------------
# Main booking serializer (read)
# ------------------------------------------------------------------
class BookingSerializer(serializers.ModelSerializer):
    client            = ClientSummarySerializer(read_only=True)
    status_display    = serializers.CharField(source="get_status_display", read_only=True)
    emergency_display = serializers.CharField(source="get_emergency_type_display", read_only=True)
    payment_display   = serializers.CharField(source="get_payment_method_display", read_only=True)
    duration_minutes  = serializers.IntegerField(read_only=True)
    has_gps           = serializers.BooleanField(read_only=True)
    is_active         = serializers.BooleanField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "reference",
            # Client / patient
            "client", "patient_name", "patient_phone", "patient_age",
            # Emergency
            "emergency_type", "emergency_display", "notes",
            # Location
            "pickup_address", "pickup_lat", "pickup_lon",
            "destination_address", "destination_lat", "destination_lon",
            # Resources
            "ambulance", "hospital",
            # Status
            "status", "status_display", "cancellation_reason",
            # Payment
            "payment_method", "payment_display", "payment_status",
            "insurance_provider", "insurance_policy_ref",
            # Fare
            "base_fare", "platform_fee", "discount", "total_fare",
            # Timestamps
            "created_at", "confirmed_at", "dispatched_at",
            "ongoing_at", "arrived_at", "completed_at", "cancelled_at",
            "updated_at",
            # Computed
            "duration_minutes", "has_gps", "is_active",
        ]
        read_only_fields = ["id", "reference", "created_at", "updated_at"]


# ------------------------------------------------------------------
# Shared hospital validator (reused by create & update)
# ------------------------------------------------------------------
def _validate_hospital(hospital):
    """Raise ValidationError if the hospital cannot accept new patients."""
    if hospital is None:
        return hospital
    if not hospital.is_active or not hospital.is_verified:
        raise serializers.ValidationError(
            "The selected hospital is not currently active."
        )
    if not hospital.is_accepting_patients:
        raise serializers.ValidationError(
            f"{hospital.name} is not accepting patients right now "
            f"(status: {hospital.get_status_display()})."
        )
    return hospital


# ------------------------------------------------------------------
# Create serializer (write)
# ------------------------------------------------------------------
class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "patient_name", "patient_phone", "patient_age",
            "emergency_type", "notes",
            "pickup_address", "pickup_lat", "pickup_lon",
            "destination_address", "destination_lat", "destination_lon",
            # Client selects their preferred hospital at booking time.
            # Optional — operator can assign / override later via
            # AssignResourcesSerializer once the booking is confirmed.
            "hospital",
            "payment_method",
            "insurance_provider", "insurance_policy_ref",
        ]

    def validate_hospital(self, value):
        return _validate_hospital(value)

    def validate(self, attrs):
        if attrs.get("payment_method") == PaymentMethod.INSURANCE:
            if not attrs.get("insurance_provider"):
                raise serializers.ValidationError(
                    {"insurance_provider": "Required when payment method is Insurance."}
                )
        return attrs


# ------------------------------------------------------------------
# Update serializer (partial write – client-side editable fields only)
# ------------------------------------------------------------------
class BookingUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "patient_name", "patient_phone", "patient_age",
            "emergency_type", "notes",
            "pickup_address", "pickup_lat", "pickup_lon",
            "destination_address", "destination_lat", "destination_lon",
            # Allow the client to change their hospital choice before
            # the booking is dispatched.
            "hospital",
            "payment_method", "insurance_provider", "insurance_policy_ref",
        ]

    def validate_hospital(self, value):
        return _validate_hospital(value)

    def validate(self, attrs):
        instance = self.instance
        if instance and not instance.is_active:
            raise serializers.ValidationError("Cannot edit a completed or cancelled booking.")
        # Block hospital changes once the ambulance is already en route
        if "hospital" in attrs and instance:
            from .models import BookingStatus as BS
            locked_statuses = {BS.DISPATCHED, BS.ONGOING, BS.ARRIVED}
            if instance.status in locked_statuses:
                raise serializers.ValidationError(
                    {"hospital": "Cannot change the hospital after the ambulance has been dispatched."}
                )
        if attrs.get("payment_method") == PaymentMethod.INSURANCE:
            if not attrs.get("insurance_provider", getattr(instance, "insurance_provider", "")):
                raise serializers.ValidationError(
                    {"insurance_provider": "Required when payment method is Insurance."}
                )
        return attrs


# ------------------------------------------------------------------
# Operator: assign ambulance / hospital
# ------------------------------------------------------------------
class AssignResourcesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ["ambulance", "hospital"]


# ------------------------------------------------------------------
# Operator: update fare
# ------------------------------------------------------------------
class FareUpdateSerializer(serializers.Serializer):
    base_fare    = serializers.IntegerField(min_value=0)
    platform_fee = serializers.IntegerField(min_value=0, required=False)
    discount     = serializers.IntegerField(min_value=0, default=0)


# ------------------------------------------------------------------
# Status transition
# ------------------------------------------------------------------
class StatusTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=BookingStatus.choices)
    note   = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_status(self, value):
        booking = self.context.get("booking")
        if booking and not booking.can_transition_to(value):
            raise serializers.ValidationError(
                f"Cannot transition from '{booking.status}' to '{value}'."
            )
        return value


# ------------------------------------------------------------------
# Cancel
# ------------------------------------------------------------------
class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


# ------------------------------------------------------------------
# Detail with logs (for admin / operator views)
# ------------------------------------------------------------------
class BookingDetailSerializer(BookingSerializer):
    status_logs = BookingStatusLogSerializer(many=True, read_only=True)

    class Meta(BookingSerializer.Meta):
        fields = BookingSerializer.Meta.fields + ["status_logs"]