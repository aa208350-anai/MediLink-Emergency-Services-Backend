# apps/hospitals/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Hospital, HospitalReview
from .serializers import (
    HospitalListSerializer,
    HospitalDetailSerializer,
    HospitalAdminSerializer,
    HospitalCreateSerializer,
    HospitalUpdateSerializer,
    BedCountSerializer,
    HospitalStatusSerializer,
    HospitalReviewSerializer,
    ReviewSubmitSerializer,
)
from .services import HospitalService, ReviewService


# ------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------
class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsHospitalAdminOrStaff(permissions.BasePermission):
    """The hospital's own admin_user or platform staff."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        hospital = obj if isinstance(obj, Hospital) else None
        return hospital and hospital.admin_user == request.user


# ------------------------------------------------------------------
# HospitalViewSet
# ------------------------------------------------------------------
class HospitalViewSet(viewsets.ModelViewSet):
    """
    GET    /hospitals/                        – search / list (public)
    POST   /hospitals/                        – register hospital (auth)
    GET    /hospitals/{id}/                   – detail (public)
    PATCH  /hospitals/{id}/                   – update own hospital
    DELETE /hospitals/{id}/                   – deactivate (staff)

    POST   /hospitals/{id}/verify/            – staff: verify
    POST   /hospitals/{id}/deactivate/        – staff: deactivate
    PATCH  /hospitals/{id}/feature/           – staff: toggle featured
    PATCH  /hospitals/{id}/status/            – hospital admin: set status
    PATCH  /hospitals/{id}/beds/              – hospital admin: update bed count

    POST   /hospitals/{id}/reviews/           – client: submit review
    GET    /hospitals/{id}/reviews/           – list approved reviews

    GET    /hospitals/for-emergency/          – ?emergency_type=cardiac
    GET    /hospitals/districts/              – list unique districts
    """

    queryset = Hospital.objects.all()
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["rating", "name", "created_at"]

    def get_permissions(self):
        if self.action in ("verify", "deactivate_action", "feature", "destroy"):
            return [permissions.IsAuthenticated(), IsStaff()]
        if self.action in ("update", "partial_update", "set_status", "beds"):
            return [permissions.IsAuthenticated(), IsHospitalAdminOrStaff()]
        if self.action in ("create", "submit_review"):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        user = getattr(self.request, "user", None)
        if self.action == "create":
            return HospitalCreateSerializer
        if self.action in ("update", "partial_update"):
            return HospitalUpdateSerializer
        if self.action == "beds":
            return BedCountSerializer
        if self.action == "set_status":
            return HospitalStatusSerializer
        if self.action == "submit_review":
            return ReviewSubmitSerializer
        if self.action == "reviews":
            return HospitalReviewSerializer
        if self.action == "retrieve":
            if user and user.is_staff:
                return HospitalAdminSerializer
            return HospitalDetailSerializer
        return HospitalListSerializer

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None
        if user and user.is_staff:
            qs = Hospital.objects.all()
        else:
            qs = Hospital.objects.filter(is_verified=True, is_active=True)

        # Search / filter via query params
        params = self.request.query_params
        district         = params.get("district")
        speciality       = params.get("speciality")
        hospital_type    = params.get("type")
        query            = params.get("q")
        accepting_only   = params.get("accepting", "true").lower() != "false"
        is_24h           = params.get("is_24_hours")
        has_icu          = params.get("has_icu")
        accepts_ins      = params.get("accepts_insurance")

        # Only apply service search for list action
        if self.action == "list":
            return HospitalService.search(
                district=district,
                speciality=speciality,
                hospital_type=hospital_type,
                accepting_only=accepting_only and not (user and user.is_staff),
                query=query,
                is_24_hours=True if is_24h == "true" else (False if is_24h == "false" else None),
                has_icu=True if has_icu == "true" else (False if has_icu == "false" else None),
                accepts_insurance=True if accepts_ins == "true" else (False if accepts_ins == "false" else None),
            )
        return qs

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hospital = HospitalService.create_hospital(request.user, serializer.validated_data)
        return Response(
            HospitalDetailSerializer(hospital, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        hospital = self.get_object()
        serializer = self.get_serializer(hospital, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        hospital = HospitalService.update_hospital(hospital, serializer.validated_data)
        return Response(HospitalDetailSerializer(hospital, context={"request": request}).data)

    # ------------------------------------------------------------------
    # Soft delete
    # ------------------------------------------------------------------
    def destroy(self, request, *args, **kwargs):
        hospital = self.get_object()
        HospitalService.deactivate(hospital)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # Staff actions
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, pk=None):
        hospital = self.get_object()
        hospital = HospitalService.verify(hospital)
        return Response(HospitalAdminSerializer(hospital, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate_action(self, request, pk=None):
        hospital = self.get_object()
        hospital = HospitalService.deactivate(hospital)
        return Response(HospitalAdminSerializer(hospital, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="feature")
    def feature(self, request, pk=None):
        hospital = self.get_object()
        featured = request.data.get("is_featured", True)
        hospital = HospitalService.set_featured(hospital, featured=bool(featured))
        return Response(HospitalAdminSerializer(hospital, context={"request": request}).data)

    # ------------------------------------------------------------------
    # Hospital-admin actions
    # ------------------------------------------------------------------
    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        hospital = self.get_object()
        serializer = HospitalStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hospital = HospitalService.set_status(hospital, serializer.validated_data["status"])
        return Response(HospitalDetailSerializer(hospital, context={"request": request}).data)

    @action(detail=True, methods=["patch"], url_path="beds")
    def beds(self, request, pk=None):
        hospital = self.get_object()
        serializer = BedCountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        hospital = HospitalService.update_bed_count(
            hospital, total=d["total_beds"], available=d["available_beds"]
        )
        return Response(HospitalDetailSerializer(hospital, context={"request": request}).data)

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------
    @action(detail=True, methods=["get", "post"], url_path="reviews")
    def reviews(self, request, pk=None):
        hospital = self.get_object()

        if request.method == "GET":
            qs = hospital.reviews.filter(is_approved=True).select_related("reviewer")
            serializer = HospitalReviewSerializer(qs, many=True, context={"request": request})
            return Response(serializer.data)

        # POST — authenticated clients only
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required to submit a review.")

        serializer = ReviewSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        from bookings.models import Booking
        booking = get_object_or_404(Booking, pk=d["booking_id"])
        review = ReviewService.submit_review(
            reviewer=request.user,
            hospital=hospital,
            booking=booking,
            rating=d["rating"],
            comment=d.get("comment", ""),
        )
        return Response(
            HospitalReviewSerializer(review, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # Discovery shortcuts
    # ------------------------------------------------------------------
    @action(detail=False, methods=["get"], url_path="for-emergency")
    def for_emergency(self, request):
        emergency_type = request.query_params.get("emergency_type", "")
        qs = HospitalService.get_for_emergency(emergency_type)
        serializer = HospitalListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="districts")
    def districts(self, request):
        districts = (
            Hospital.objects.filter(is_verified=True, is_active=True)
            .values_list("district", flat=True)
            .distinct()
            .order_by("district")
        )
        return Response(list(districts))


# ------------------------------------------------------------------
# Review moderation ViewSet (staff only)
# ------------------------------------------------------------------
class ReviewModerationViewSet(viewsets.ViewSet):
    """
    GET    /reviews/pending/         – list unapproved reviews
    POST   /reviews/{id}/approve/    – approve
    DELETE /reviews/{id}/reject/     – reject & delete
    """
    permission_classes = [permissions.IsAuthenticated, IsStaff]

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        qs = HospitalReview.objects.filter(is_approved=False).select_related("hospital", "reviewer")
        serializer = HospitalReviewSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        review = get_object_or_404(HospitalReview, pk=pk)
        review = ReviewService.approve_review(review)
        return Response(HospitalReviewSerializer(review, context={"request": request}).data)

    @action(detail=True, methods=["delete"], url_path="reject")
    def reject(self, request, pk=None):
        review = get_object_or_404(HospitalReview, pk=pk)
        ReviewService.reject_review(review)
        return Response(status=status.HTTP_204_NO_CONTENT)