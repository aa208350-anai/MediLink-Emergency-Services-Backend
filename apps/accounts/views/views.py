from __future__ import annotations
from typing import TYPE_CHECKING
# apps/accounts/views.py
from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from apps.accounts.models.constants import AccountType
from apps.accounts.services.registration_services import RegistrationService
from apps.accounts.serializers import (
    UserSerializer,
    UserListSerializer,
    AdminUserUpdateSerializer,
    RegisterClientSerializer,
    RegisterDriverSerializer,
    RegisterProviderAdminSerializer,
    LoginSerializer,
    VerifyEmailSerializer,
    ResendVerificationSerializer,
    ChangePasswordSerializer,
    RequestPasswordResetSerializer,
    ConfirmPasswordResetSerializer,
    UpdateBasicInfoSerializer,
    UpdateClientProfileSerializer,
    UpdateDriverProfileSerializer,
    UpdateProviderAdminProfileSerializer,
    UpdateStaffProfileSerializer,
)

if TYPE_CHECKING:
    from apps.accounts.models import CustomUser  
User = get_user_model()


def _jwt_for_user(user: CustomUser) -> dict:
    """Return { access, refresh } JWT pair for a user."""
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


# 
# Registration
# 

class RegisterClientView(APIView):
    """POST /auth/register/client/"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterClientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = RegistrationService.register_client(**serializer.validated_data)
        return Response(
            {"detail": "Account created successfully."},
            status=status.HTTP_201_CREATED,
        )



class RegisterDriverView(APIView):
    """POST /auth/register/driver/"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = RegistrationService.register_driver(**serializer.validated_data)
        return Response(
            {"detail": "Driver account created successfully."},
            status=status.HTTP_201_CREATED,
        )


class RegisterProviderAdminView(APIView):
    """POST /auth/register/provider/"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterProviderAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = RegistrationService.register_provider_admin(**serializer.validated_data)
        return Response(
            {"detail": "Provider account created successfully."},
            status=status.HTTP_201_CREATED,
        )
 
# Email verification

class VerifyEmailView(APIView):
    """POST /auth/verify-email/"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.accounts.models.email_verification import EmailVerification

        try:
            verification = EmailVerification.objects.get(
                token=serializer.validated_data["token"],
                otp=serializer.validated_data["otp"],
                is_used=False,
            )
        except EmailVerification.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.is_expired():
            return Response(
                {"detail": "Verification code has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = verification.user
        user.is_active = True
        user.save(update_fields=["is_active"])
        verification.is_used = True
        verification.save(update_fields=["is_used"])

        tokens = _jwt_for_user(user)
        return Response({
            "detail": "Email verified successfully.",
            "user": UserSerializer(user, context={"request": request}).data,
            **tokens,
        })


class ResendVerificationView(APIView):
    """POST /auth/resend-verification/"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                RegistrationService._send_verification(user)
        except User.DoesNotExist:
            pass  # Don't reveal whether email exists

        return Response({"detail": "If that email is registered and unverified, a new code has been sent."})

# Login / Logout 

class LoginView(APIView):
    """POST /auth/login/"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user   = serializer.validated_data["user"]
        tokens = _jwt_for_user(user)
        return Response({
            "user": UserSerializer(user, context={"request": request}).data,
            **tokens,
        })


class LogoutView(APIView):
    """POST /auth/logout/  — blacklists the refresh token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass  # Already blacklisted or invalid — that's fine
        return Response({"detail": "Logged out successfully."})

# Current user

class MeView(APIView):
    """GET /auth/me/   PATCH /auth/me/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        serializer = UpdateBasicInfoSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user, context={"request": request}).data)

# Profile update (role-aware) 

class ProfileView(APIView):
    """GET /auth/profile/   PATCH /auth/profile/"""
    permission_classes = [permissions.IsAuthenticated]

    PROFILE_MAP = {
        AccountType.CLIENT:         ("client_profile",         UpdateClientProfileSerializer),
        AccountType.DRIVER:         ("driver_profile",         UpdateDriverProfileSerializer),
        AccountType.PROVIDER_ADMIN: ("provider_admin_profile", UpdateProviderAdminProfileSerializer),
        AccountType.STAFF:          ("staff_profile",          UpdateStaffProfileSerializer),
    }

    def _get_profile(self, user):
        attr, _ = self.PROFILE_MAP.get(user.role, (None, None))
        if attr is None:
            raise PermissionDenied("Profile management not available for this role.")
        profile = getattr(user, attr, None)
        if profile is None:
            raise NotFound("Profile not found.")
        return profile, self.PROFILE_MAP[user.role][1]

    def get(self, request):
        profile, Serializer = self._get_profile(request.user)
        return Response(Serializer(profile, context={"request": request}).data)

    def patch(self, request):
        profile, Serializer = self._get_profile(request.user)
        serializer = Serializer(profile, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user, context={"request": request}).data)

# Password management 

class ChangePasswordView(APIView):
    """POST /auth/change-password/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        # Re-issue tokens so existing sessions aren't broken
        tokens = _jwt_for_user(request.user)
        return Response({"detail": "Password changed successfully.", **tokens})


class RequestPasswordResetView(APIView):
    """POST /auth/password-reset/"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # TODO: implement password reset emails when email is re-enabled
        return Response({"detail": "Password reset is not available at this time."})


class ConfirmPasswordResetView(APIView):
    """POST /auth/password-reset/confirm/"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ConfirmPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.accounts.models.email_verification import EmailVerification

        try:
            verification = EmailVerification.objects.get(
                token=serializer.validated_data["token"],
                otp=serializer.validated_data["otp"],
                is_used=False,
            )
        except EmailVerification.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired reset code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.is_expired():
            return Response(
                {"detail": "Reset code has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = verification.user
        user.set_password(serializer.validated_data["new_password"])
        user.is_active = True  # Reactivate in case account was inactive
        user.save(update_fields=["password", "is_active"])
        verification.is_used = True
        verification.save(update_fields=["is_used"])

        tokens = _jwt_for_user(user)
        return Response({"detail": "Password reset successfully.", **tokens})


# 
# Role upgrade (authenticated)
# 

class UpgradeToDriverView(APIView):
    """POST /auth/upgrade/driver/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role == AccountType.DRIVER:
            return Response({"detail": "You are already a driver."}, status=status.HTTP_400_BAD_REQUEST)
        user = RegistrationService.upgrade_to_driver(user=request.user, **request.data)
        return Response(UserSerializer(user, context={"request": request}).data)


class UpgradeToProviderAdminView(APIView):
    """POST /auth/upgrade/provider/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role == AccountType.PROVIDER_ADMIN:
            return Response({"detail": "You are already a provider admin."}, status=status.HTTP_400_BAD_REQUEST)
        user = RegistrationService.upgrade_to_provider_admin(user=request.user, **request.data)
        return Response(UserSerializer(user, context={"request": request}).data)


# 
# Admin: user management
# 

class IsAdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser or
            request.user.role == AccountType.ADMIN
        )


class UserListView(generics.ListAPIView):
    """GET /auth/admin/users/?role=client&is_active=true"""
    permission_classes = [IsAdminPermission]
    serializer_class = UserListSerializer

    def get_queryset(self):
        qs = User.objects.all().order_by("-created_at")
        role      = self.request.query_params.get("role")
        is_active = self.request.query_params.get("is_active")
        if role:
            qs = qs.filter(role=role)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs


class UserDetailView(generics.RetrieveUpdateAPIView):
    """GET / PATCH /auth/admin/users/{id}/"""
    permission_classes = [IsAdminPermission]
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return AdminUserUpdateSerializer
        return UserSerializer


class VerifyProfileView(APIView):
    """POST /auth/admin/users/{id}/verify/  — verify a driver or provider admin."""
    permission_classes = [IsAdminPermission]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise NotFound("User not found.")

        profile = None
        if user.role == AccountType.DRIVER:
            profile = getattr(user, "driver_profile", None)
        elif user.role == AccountType.PROVIDER_ADMIN:
            profile = getattr(user, "provider_admin_profile", None)

        if profile is None:
            return Response(
                {"detail": "This user's role does not support verification."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile.verify(verified_by=request.user)
        return Response(UserSerializer(user, context={"request": request}).data)