# apps/ambulances/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from .models import Ambulance, Provider
from .serializers import (
    ProviderSerializer,
    ProviderCreateSerializer,
    ProviderUpdateSerializer,
    AmbulanceSerializer,
    AmbulanceCreateSerializer,
    AmbulanceUpdateSerializer,
    AmbulanceStatusSerializer,
    AmbulanceLocationSerializer,
    AssignDriverSerializer,
)
from .services import ProviderService, AmbulanceService

User = get_user_model()


# ------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------
class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsProviderAdminOrAdmin(permissions.BasePermission):
    """Allow the provider's own admin_user or a platform admin."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        # obj could be Provider or Ambulance
        provider = obj if isinstance(obj, Provider) else getattr(obj, "provider", None)
        return provider and provider.admin_user == request.user


class IsDriverOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.driver == request.user


# ------------------------------------------------------------------
# ProviderViewSet
# ------------------------------------------------------------------
class ProviderViewSet(viewsets.ModelViewSet):
    """
    GET    /providers/              – list verified & active (public)
    POST   /providers/              – register provider (auth required)
    GET    /providers/{id}/         – detail
    PATCH  /providers/{id}/         – update own provider
    DELETE /providers/{id}/         – deactivate (staff)

    POST   /providers/{id}/verify/  – staff: verify provider
    POST   /providers/{id}/deactivate/ – staff: deactivate
    GET    /providers/{id}/ambulances/ – list provider's ambulances
    """

    queryset = Provider.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "district", "phone"]
    ordering_fields = ["name", "rating", "created_at"]

    def get_permissions(self):
        if self.action in ("verify", "deactivate", "destroy"):
            return [permissions.IsAuthenticated(), IsAdminUser()]
        if self.action in ("update", "partial_update"):
            return [permissions.IsAuthenticated(), IsProviderAdminOrAdmin()]
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action == "create":
            return ProviderCreateSerializer
        if self.action in ("update", "partial_update"):
            return ProviderUpdateSerializer
        return ProviderSerializer

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        qs = Provider.objects.all()
        # Non-staff only see verified + active providers
        if not (user and user.is_staff):
            qs = qs.filter(is_verified=True, is_active=True)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = ProviderService.create_provider(request.user, serializer.validated_data)
        return Response(
            ProviderSerializer(provider, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        provider = self.get_object()
        ProviderService.deactivate_provider(provider)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, pk=None):
        provider = self.get_object()
        provider = ProviderService.verify_provider(provider, verified_by=request.user)
        return Response(ProviderSerializer(provider, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        provider = self.get_object()
        provider = ProviderService.deactivate_provider(provider)
        return Response(ProviderSerializer(provider, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path="ambulances")
    def ambulances(self, request, pk=None):
        provider = self.get_object()
        qs = AmbulanceService.get_for_provider(provider)
        serializer = AmbulanceSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


# ------------------------------------------------------------------
# AmbulanceViewSet
# ------------------------------------------------------------------
class AmbulanceViewSet(viewsets.ModelViewSet):
    """
    GET    /ambulances/                      – list available (public)
    POST   /ambulances/                      – provider admin: add ambulance
    GET    /ambulances/{id}/                 – detail
    PATCH  /ambulances/{id}/                 – provider admin: update
    DELETE /ambulances/{id}/                 – provider admin: deactivate

    PATCH  /ambulances/{id}/status/          – operator / provider admin
    PATCH  /ambulances/{id}/location/        – driver: update GPS
    PATCH  /ambulances/{id}/assign-driver/   – provider admin: assign driver
    DELETE /ambulances/{id}/unassign-driver/ – provider admin: unassign driver
    GET    /ambulances/available/            – all available ambulances
    """

    queryset = Ambulance.objects.select_related("provider", "driver").all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["plate_number", "provider__name", "vehicle_make", "vehicle_model"]
    ordering_fields = ["created_at", "base_fare", "provider__name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy",
                           "assign_driver", "unassign_driver"):
            return [permissions.IsAuthenticated(), IsProviderAdminOrAdmin()]
        if self.action == "location":
            return [permissions.IsAuthenticated(), IsDriverOrAdmin()]
        if self.action == "set_status":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action == "create":
            return AmbulanceCreateSerializer
        if self.action in ("update", "partial_update"):
            return AmbulanceUpdateSerializer
        if self.action == "set_status":
            return AmbulanceStatusSerializer
        if self.action == "location":
            return AmbulanceLocationSerializer
        if self.action == "assign_driver":
            return AssignDriverSerializer
        return AmbulanceSerializer

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        qs = Ambulance.objects.select_related("provider", "driver")

        # Filter by query params
        ambulance_type = self.request.query_params.get("type")
        provider_id    = self.request.query_params.get("provider")

        if ambulance_type:
            qs = qs.filter(ambulance_type=ambulance_type)
        if provider_id:
            qs = qs.filter(provider_id=provider_id)

        # Non-staff only see active ambulances
        if not (user and user.is_staff):
            qs = qs.filter(is_active=True)

        return qs

    def create(self, request, *args, **kwargs):
        # Derive provider from the requesting user
        provider = get_object_or_404(Provider, admin_user=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ambulance = AmbulanceService.create_ambulance(provider, serializer.validated_data)
        return Response(
            AmbulanceSerializer(ambulance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        ambulance = self.get_object()
        ambulance.is_active = False
        ambulance.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        ambulance = self.get_object()
        # Drivers can only update their own ambulance's status
        if not request.user.is_staff:
            if ambulance.driver != request.user and not hasattr(request.user, "provider"):
                raise PermissionDenied("You can only update status for your assigned ambulance.")
        serializer = AmbulanceStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ambulance = AmbulanceService.set_status(ambulance, serializer.validated_data["status"])
        return Response(AmbulanceSerializer(ambulance, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="location")
    def location(self, request, pk=None):
        ambulance = self.get_object()
        serializer = AmbulanceLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ambulance = AmbulanceService.update_location(
            ambulance,
            lat=serializer.validated_data["latitude"],
            lon=serializer.validated_data["longitude"],
        )
        return Response(AmbulanceSerializer(ambulance, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="assign-driver")
    def assign_driver(self, request, pk=None):
        ambulance = self.get_object()
        serializer = AssignDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        driver = get_object_or_404(User, pk=serializer.validated_data["driver_id"])
        ambulance = AmbulanceService.assign_driver(ambulance, driver)
        return Response(AmbulanceSerializer(ambulance, context={"request": request}).data)

    @action(detail=True, methods=["delete"], url_path="unassign-driver")
    def unassign_driver(self, request, pk=None):
        ambulance = self.get_object()
        ambulance = AmbulanceService.unassign_driver(ambulance)
        return Response(AmbulanceSerializer(ambulance, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="available")
    def available(self, request):
        provider_id = request.query_params.get("provider")
        provider = None
        if provider_id:
            provider = get_object_or_404(Provider, pk=provider_id)
        qs = AmbulanceService.get_available(provider=provider)
        serializer = AmbulanceSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)