# apps/hospitals/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Hospital, HospitalReview, HospitalStatus, Speciality, HospitalType

User = get_user_model()


# ------------------------------------------------------------------
# Nested helpers
# ------------------------------------------------------------------
class AdminUserSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "email"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email


# ------------------------------------------------------------------
# Review serializers
# ------------------------------------------------------------------
class HospitalReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = HospitalReview
        fields = [
            "id", "reviewer_name", "rating", "comment",
            "is_approved", "created_at",
        ]
        read_only_fields = ["id", "is_approved", "created_at"]

    def get_reviewer_name(self, obj):
        if obj.reviewer:
            return obj.reviewer.get_full_name() or obj.reviewer.email
        return "Anonymous"


class ReviewSubmitSerializer(serializers.Serializer):
    booking_id = serializers.UUIDField()
    rating     = serializers.IntegerField(min_value=1, max_value=5)
    comment    = serializers.CharField(required=False, allow_blank=True, default="")


# ------------------------------------------------------------------
# Hospital list (public, minimal)
# ------------------------------------------------------------------
class HospitalListSerializer(serializers.ModelSerializer):
    type_display   = serializers.CharField(source="get_hospital_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_accepting   = serializers.BooleanField(source="is_accepting_patients", read_only=True)
    bed_occupancy  = serializers.FloatField(source="bed_occupancy_pct", read_only=True)

    class Meta:
        model = Hospital
        fields = [
            "id", "name", "hospital_type", "type_display",
            "district", "address", "latitude", "longitude",
            "phone_primary", "phone_emergency", "is_24_hours",
            "status", "status_display", "is_accepting",
            "rating", "review_count",
            "has_icu", "has_maternity", "accepts_insurance",
            "specialities", "available_beds", "bed_occupancy",
            "is_featured",
        ]


# ------------------------------------------------------------------
# Hospital detail (public, full)
# ------------------------------------------------------------------
class HospitalDetailSerializer(HospitalListSerializer):
    reviews     = serializers.SerializerMethodField()
    has_gps     = serializers.BooleanField(read_only=True)

    class Meta(HospitalListSerializer.Meta):
        fields = HospitalListSerializer.Meta.fields + [
            "description", "email", "website",
            "registration_no", "total_beds",
            "has_blood_bank", "has_ambulance",
            "has_gps", "created_at", "reviews",
        ]

    def get_reviews(self, obj):
        approved = obj.reviews.filter(is_approved=True)[:10]
        return HospitalReviewSerializer(approved, many=True).data


# ------------------------------------------------------------------
# Hospital create (hospital admin / staff)
# ------------------------------------------------------------------
class HospitalCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = [
            "name", "hospital_type", "registration_no", "description",
            "phone_primary", "phone_emergency", "email", "website",
            "address", "district", "latitude", "longitude",
            "specialities", "has_icu", "has_maternity",
            "has_blood_bank", "has_ambulance", "accepts_insurance", "is_24_hours",
            "total_beds", "available_beds",
        ]

    def validate_specialities(self, value):
        valid = {s.value for s in Speciality}
        invalid = [v for v in value if v not in valid]
        if invalid:
            raise serializers.ValidationError(f"Invalid specialities: {invalid}")
        return value


# ------------------------------------------------------------------
# Hospital update (hospital admin — own profile)
# ------------------------------------------------------------------
class HospitalUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = [
            "name", "description",
            "phone_primary", "phone_emergency", "email", "website",
            "address", "district", "latitude", "longitude",
            "specialities", "has_icu", "has_maternity",
            "has_blood_bank", "has_ambulance", "accepts_insurance", "is_24_hours",
        ]

    def validate_specialities(self, value):
        valid = {s.value for s in Speciality}
        invalid = [v for v in value if v not in valid]
        if invalid:
            raise serializers.ValidationError(f"Invalid specialities: {invalid}")
        return value


# ------------------------------------------------------------------
# Bed count update
# ------------------------------------------------------------------
class BedCountSerializer(serializers.Serializer):
    total_beds     = serializers.IntegerField(min_value=0)
    available_beds = serializers.IntegerField(min_value=0)

    def validate(self, attrs):
        if attrs["available_beds"] > attrs["total_beds"]:
            raise serializers.ValidationError(
                {"available_beds": "Cannot exceed total beds."}
            )
        return attrs


# ------------------------------------------------------------------
# Status update (operator)
# ------------------------------------------------------------------
class HospitalStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=HospitalStatus.choices)


# ------------------------------------------------------------------
# Admin-level full serializer (staff view)
# ------------------------------------------------------------------
class HospitalAdminSerializer(HospitalDetailSerializer):
    admin_user = AdminUserSummarySerializer(read_only=True)

    class Meta(HospitalDetailSerializer.Meta):
        fields = HospitalDetailSerializer.Meta.fields + [
            "admin_user", "is_verified", "is_active", "is_featured", "updated_at",
        ]