# apps/ambulances/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Ambulance, AmbulanceStatus, AmbulanceType, Provider

User = get_user_model()


# ------------------------------------------------------------------
# Nested helpers
# ------------------------------------------------------------------
class DriverSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "email"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.email


class ProviderSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ["id", "name", "phone", "district", "is_verified", "rating"]


# ------------------------------------------------------------------
# Provider
# ------------------------------------------------------------------
class ProviderSerializer(serializers.ModelSerializer):
    ambulance_count = serializers.SerializerMethodField()

    class Meta:
        model = Provider
        fields = [
            "id", "name", "description", "phone", "address",
            "district", "is_verified", "is_active", "rating",
            "ambulance_count", "created_at",
        ]
        read_only_fields = ["id", "is_verified", "rating", "created_at"]

    def get_ambulance_count(self, obj):
        return obj.ambulances.filter(is_active=True).count()


class ProviderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ["name", "description", "phone", "address", "district"]


class ProviderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ["name", "description", "phone", "address", "district", "is_active"]


# ------------------------------------------------------------------
# Ambulance
# ------------------------------------------------------------------
class AmbulanceSerializer(serializers.ModelSerializer):
    provider        = ProviderSummarySerializer(read_only=True)
    driver          = DriverSummarySerializer(read_only=True)
    status_display  = serializers.CharField(source="get_status_display", read_only=True)
    type_display    = serializers.CharField(source="get_ambulance_type_display", read_only=True)
    is_available    = serializers.BooleanField(read_only=True)

    class Meta:
        model = Ambulance
        fields = [
            "id", "provider", "plate_number",
            "vehicle_make", "vehicle_model", "vehicle_year",
            "ambulance_type", "type_display",
            "status", "status_display", "is_available",
            "latitude", "longitude",
            "driver",
            "base_fare", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AmbulanceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ambulance
        fields = [
            "plate_number", "vehicle_make", "vehicle_model",
            "vehicle_year", "ambulance_type", "base_fare",
        ]

    def validate_plate_number(self, value):
        if Ambulance.objects.filter(plate_number__iexact=value).exists():
            raise serializers.ValidationError("An ambulance with this plate number already exists.")
        return value.upper()


class AmbulanceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ambulance
        fields = [
            "vehicle_make", "vehicle_model", "vehicle_year",
            "ambulance_type", "base_fare", "is_active",
        ]


class AmbulanceStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=AmbulanceStatus.choices)


class AmbulanceLocationSerializer(serializers.Serializer):
    latitude  = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)


class AssignDriverSerializer(serializers.Serializer):
    driver_id = serializers.UUIDField()

    def validate_driver_id(self, value):
        User = __import__("django.contrib.auth", fromlist=["get_user_model"]).get_user_model()
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Driver not found.")
        return value