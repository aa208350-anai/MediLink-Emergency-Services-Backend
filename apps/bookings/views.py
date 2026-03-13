# apps/bookings/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Booking, BookingStatus
from .serializers import (
    BookingSerializer,
    BookingDetailSerializer,
    BookingCreateSerializer,
    BookingUpdateSerializer,
    AssignResourcesSerializer,
    FareUpdateSerializer,
    StatusTransitionSerializer,
    CancelSerializer,
    BookingStatusLogSerializer,
)
from .services import BookingService


# ------------------------------------------------------------------
# Permission helpers
# ------------------------------------------------------------------
class IsOperatorOrAdmin(permissions.BasePermission):
    """Allow staff / admin users."""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser
        )


class IsOwnerOrOperator(permissions.BasePermission):
    """Allow the booking's client or staff."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        return obj.client == request.user


# ------------------------------------------------------------------
# Main ViewSet
# ------------------------------------------------------------------
class BookingViewSet(viewsets.ModelViewSet):
    """
    Client-facing + operator booking API.

    Endpoints
    ---------
    GET    /bookings/                  – list own bookings (clients) or all (staff)
    POST   /bookings/                  – create booking
    GET    /bookings/{id}/             – retrieve detail with status logs
    PATCH  /bookings/{id}/             – update editable fields
    DELETE /bookings/{id}/             – soft-delete (staff only)

    POST   /bookings/{id}/confirm/     – operator: confirm
    POST   /bookings/{id}/dispatch/    – operator: dispatch  ← url_path kept, method renamed
    POST   /bookings/{id}/ongoing/     – driver: mark en-route
    POST   /bookings/{id}/arrived/     – driver: mark arrived
    POST   /bookings/{id}/complete/    – operator: complete
    POST   /bookings/{id}/cancel/      – client or operator: cancel

    PATCH  /bookings/{id}/assign/      – operator: assign ambulance / hospital
    PATCH  /bookings/{id}/fare/        – operator: update fare
    POST   /bookings/{id}/transition/  – operator: generic status transition
    GET    /bookings/{id}/logs/        – status audit trail
    GET    /bookings/active/           – client: active bookings shortcut
    GET    /bookings/history/          – client: completed / cancelled bookings
    """

    queryset = Booking.objects.select_related("client", "ambulance", "hospital").prefetch_related("status_logs")
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrOperator]

    # ------------------------------------------------------------------
    # Serializer routing
    # ------------------------------------------------------------------
    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        if self.action in ("update", "partial_update"):
            return BookingUpdateSerializer
        if self.action == "retrieve":
            return BookingDetailSerializer
        if self.action == "assign":
            return AssignResourcesSerializer
        if self.action == "fare":
            return FareUpdateSerializer
        if self.action == "transition":
            return StatusTransitionSerializer
        if self.action == "cancel":
            return CancelSerializer
        if self.action == "logs":
            return BookingStatusLogSerializer
        return BookingSerializer

    # ------------------------------------------------------------------
    # Queryset scoping
    # ------------------------------------------------------------------
    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset().filter(is_deleted=False)
        if user.is_staff or user.is_superuser:
            status_filter = self.request.query_params.get("status")
            if status_filter:
                qs = qs.filter(status=status_filter)
            return qs
        # Clients see only their own
        return qs.filter(client=user)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = BookingService.create_booking(request.user, serializer.validated_data)
        return Response(
            BookingDetailSerializer(booking, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # Soft delete
    # ------------------------------------------------------------------
    def destroy(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied("Only staff can delete bookings.")
        booking = self.get_object()
        booking.is_deleted = True
        booking.save(update_fields=["is_deleted", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # Permission helper
    # ------------------------------------------------------------------
    def _require_operator(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied("Only operators/admins can perform this action.")

    # ------------------------------------------------------------------
    # Status transition actions
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        self._require_operator(request)
        booking = self.get_object()
        ambulance_id = request.data.get("ambulance")
        ambulance = None
        if ambulance_id:
            from ambulances.models import Ambulance
            ambulance = get_object_or_404(Ambulance, pk=ambulance_id)
        booking = BookingService.confirm(booking, operator=request.user, ambulance=ambulance)
        return Response(BookingDetailSerializer(booking, context={"request": request}).data)

    # ↓ Renamed from `dispatch` → `dispatch_booking` to avoid shadowing
    #   ViewSet.dispatch() — the URL path /dispatch/ is preserved via url_path.
    @action(detail=True, methods=["post"], url_path="dispatch")
    def dispatch_booking(self, request, pk=None):
        self._require_operator(request)
        booking = self.get_object()
        ambulance_id = request.data.get("ambulance")
        ambulance = None
        if ambulance_id:
            from ambulances.models import Ambulance
            ambulance = get_object_or_404(Ambulance, pk=ambulance_id)
        booking = BookingService.dispatch(booking, operator=request.user, ambulance=ambulance)
        return Response(BookingDetailSerializer(booking, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="ongoing")
    def ongoing(self, request, pk=None):
        booking = self.get_object()
        booking = BookingService.mark_ongoing(booking, driver=request.user)
        return Response(BookingDetailSerializer(booking, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="arrived")
    def arrived(self, request, pk=None):
        booking = self.get_object()
        booking = BookingService.mark_arrived(booking, driver=request.user)
        return Response(BookingDetailSerializer(booking, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        self._require_operator(request)
        booking = self.get_object()
        note = request.data.get("note", "")
        booking = BookingService.complete(booking, operator=request.user, note=note)
        return Response(BookingDetailSerializer(booking, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if not (request.user.is_staff or request.user.is_superuser or booking.client == request.user):
            raise PermissionDenied("You do not have permission to cancel this booking.")
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = BookingService.cancel(
            booking, cancelled_by=request.user, reason=serializer.validated_data.get("reason", "")
        )
        return Response(BookingDetailSerializer(booking, context={"request": request}).data)

    # ------------------------------------------------------------------
    # Operator utilities
    # ------------------------------------------------------------------
    @action(detail=True, methods=["patch"], url_path="assign")
    def assign(self, request, pk=None):
        self._require_operator(request)
        booking = self.get_object()
        serializer = AssignResourcesSerializer(booking, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(BookingDetailSerializer(booking, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="fare")
    def fare(self, request, pk=None):
        self._require_operator(request)
        booking = self.get_object()
        serializer = FareUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        booking = BookingService.update_fare(
            booking,
            base_fare=d["base_fare"],
            platform_fee=d.get("platform_fee"),
            discount=d.get("discount", 0),
        )
        return Response(BookingDetailSerializer(booking, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, pk=None):
        self._require_operator(request)
        booking = self.get_object()
        serializer = StatusTransitionSerializer(data=request.data, context={"booking": booking})
        serializer.is_valid(raise_exception=True)
        booking = BookingService.transition(
            booking,
            new_status=serializer.validated_data["status"],
            changed_by=request.user,
            note=serializer.validated_data.get("note", ""),
        )
        return Response(BookingDetailSerializer(booking, context={"request": request}).data)

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------
    @action(detail=True, methods=["get"], url_path="logs")
    def logs(self, request, pk=None):
        booking = self.get_object()
        logs = booking.status_logs.select_related("changed_by").all()
        serializer = BookingStatusLogSerializer(logs, many=True, context={"request": request})
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # List shortcuts
    # ------------------------------------------------------------------
    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        qs = BookingService.get_active_for_client(request.user)
        serializer = BookingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        qs = BookingService.get_history_for_client(request.user)
        serializer = BookingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)