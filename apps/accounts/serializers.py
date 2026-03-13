# apps/accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.accounts.models.constants import AccountType
from apps.accounts.models.profile import (
    ClientProfile,
    DriverProfile,
    StaffProfile,
    ProviderAdminProfile,
    AdminProfile,
)

User = get_user_model()


# 
# Helpers
# 

def _validate_password_strength(value):
    try:
        validate_password(value)
    except DjangoValidationError as e:
        raise serializers.ValidationError(list(e.messages))
    return value


# 
# Profile serializers (nested read)
# 

class ClientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientProfile
        fields = [
            "id", "phone", "whatsapp_number",
            "date_of_birth", "additional_notes",
            "profile_photo", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = [
            "id", "phone", "whatsapp_number",
            "profile_photo",
            "license_number", "license_expiry_date",
            "national_id_front", "national_id_back",
            "vehicle_make", "vehicle_model", "vehicle_year",
            "vehicle_plate", "vehicle_color",
            "is_available", "is_verified",
            "average_rating", "total_reviews", "total_trips",
            "created_at",
        ]
        read_only_fields = ["id", "is_verified", "average_rating", "total_reviews", "total_trips", "created_at"]


class StaffProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffProfile
        fields = [
            "id", "phone", "profile_photo",
            "department", "job_title", "employee_id",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProviderAdminProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderAdminProfile
        fields = [
            "id", "phone", "whatsapp_number",
            "profile_photo", "company_logo",
            "company_name", "company_registration_number",
            "company_website", "office_address", "office_phone",
            "tin_number", "facebook_page", "instagram_handle",
            "is_verified",
            "average_rating", "total_reviews", "total_transactions",
            "created_at",
        ]
        read_only_fields = ["id", "is_verified", "average_rating", "total_reviews", "total_transactions", "created_at"]


class AdminProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminProfile
        fields = [
            "id", "phone", "profile_photo",
            "can_create_users", "can_verify_profiles",
            "can_manage_drivers", "can_manage_providers",
            "can_manage_payments", "can_manage_staff",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# 
# User read serializer (returned on me / detail)
# 

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name_or_email", read_only=True)
    profile   = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "role", "is_active", "is_staff",
            "created_at", "updated_at", "last_login",
            "profile",
        ]
        read_only_fields = ["id", "role", "is_active", "is_staff", "created_at", "updated_at", "last_login"]

    def get_profile(self, obj):
        role_map = {
            AccountType.CLIENT:         ("client_profile",         ClientProfileSerializer),
            AccountType.DRIVER:         ("driver_profile",         DriverProfileSerializer),
            AccountType.STAFF:          ("staff_profile",          StaffProfileSerializer),
            AccountType.PROVIDER_ADMIN: ("provider_admin_profile", ProviderAdminProfileSerializer),
            AccountType.ADMIN:          ("admin_profile",          AdminProfileSerializer),
        }
        attr, Serializer = role_map.get(obj.role, (None, None))
        if attr and hasattr(obj, attr):
            profile = getattr(obj, attr, None)
            if profile:
                return Serializer(profile, context=self.context).data
        return None


# 
# Registration serializers
# 

class BaseRegisterSerializer(serializers.Serializer):
    email      = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name  = serializers.CharField(max_length=150)
    password   = serializers.CharField(write_only=True, validators=[_validate_password_strength])
    phone      = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class RegisterClientSerializer(BaseRegisterSerializer):
    pass


class RegisterDriverSerializer(BaseRegisterSerializer):
    license_number      = serializers.CharField(max_length=50, required=False, allow_blank=True)
    license_expiry_date = serializers.DateField(required=False, allow_null=True)
    vehicle_make        = serializers.CharField(max_length=100, required=False, allow_blank=True)
    vehicle_model       = serializers.CharField(max_length=100, required=False, allow_blank=True)
    vehicle_plate       = serializers.CharField(max_length=20, required=False, allow_blank=True)


class RegisterProviderAdminSerializer(BaseRegisterSerializer):
    company_name                = serializers.CharField(max_length=150, required=False, allow_blank=True)
    company_registration_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    office_address              = serializers.CharField(required=False, allow_blank=True)
    office_phone                = serializers.CharField(max_length=20, required=False, allow_blank=True)


# 
# Login / token
# 

class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate
        email    = attrs["email"].lower().strip()
        password = attrs["password"]
        user     = authenticate(request=self.context.get("request"), email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated. Please contact support.")
        attrs["user"] = user
        return attrs


# 
# Email verification
# 

class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()
    otp   = serializers.CharField(min_length=6, max_length=6)


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.lower().strip()
        if not User.objects.filter(email=value).exists():
            # Don't reveal whether email exists — silently accept
            pass
        return value


# 
# Password
# 

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password     = serializers.CharField(write_only=True, validators=[_validate_password_strength])

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()


class ConfirmPasswordResetSerializer(serializers.Serializer):
    token        = serializers.CharField()
    otp          = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(write_only=True, validators=[_validate_password_strength])


# 
# Profile update serializers (per-role)
# 

class UpdateClientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientProfile
        fields = ["phone", "whatsapp_number", "date_of_birth", "additional_notes", "profile_photo"]


class UpdateDriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = [
            "phone", "whatsapp_number", "profile_photo",
            "license_number", "license_expiry_date",
            "national_id_front", "national_id_back",
            "vehicle_make", "vehicle_model", "vehicle_year",
            "vehicle_plate", "vehicle_color",
            "is_available",
        ]


class UpdateProviderAdminProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderAdminProfile
        fields = [
            "phone", "whatsapp_number", "profile_photo", "company_logo",
            "company_name", "company_registration_number",
            "company_website", "office_address", "office_phone",
            "tin_number", "facebook_page", "instagram_handle",
        ]


class UpdateStaffProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffProfile
        fields = ["phone", "profile_photo", "department", "job_title"]


class UpdateBasicInfoSerializer(serializers.ModelSerializer):
    """Update first_name / last_name on the User model itself."""
    class Meta:
        model = User
        fields = ["first_name", "last_name"]


# 
# Admin: user list / management
# 

class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name_or_email", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "role",
            "is_active", "is_staff", "created_at",
        ]


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Staff-only: change role, activate/deactivate."""
    class Meta:
        model = User
        fields = ["role", "is_active", "is_staff"]