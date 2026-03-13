# apps/accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from apps.accounts.models.customuser import CustomUser
from apps.accounts.models.profile import (
    AdminProfile,
    ClientProfile,
    DriverProfile,
    ProviderAdminProfile,
    StaffProfile,
)

# PROFILE INLINES
class ClientProfileInline(admin.StackedInline):
    model = ClientProfile
    can_delete = False
    verbose_name_plural = "Client Profile"
    fk_name = "user"
    fields = ("profile_photo", "phone", "whatsapp_number", "date_of_birth", "additional_notes")
    extra = 0


class DriverProfileInline(admin.StackedInline):
    model = DriverProfile
    can_delete = False
    verbose_name_plural = "Driver Profile"
    fk_name = "user"
    fields = (
        "profile_photo", "phone", "whatsapp_number",
        "national_id_front", "national_id_back",
        "license_number", "license_expiry_date",
        "vehicle_make", "vehicle_model", "vehicle_year", "vehicle_plate", "vehicle_color",
        "is_available", "is_verified", "verified_at",
        "average_rating", "total_reviews", "total_trips",
    )
    readonly_fields = ("average_rating", "total_reviews", "total_trips", "verified_at")
    extra = 0


class StaffProfileInline(admin.StackedInline):
    model = StaffProfile
    can_delete = False
    verbose_name_plural = "Staff Profile"
    fk_name = "user"
    fields = ("profile_photo", "phone", "department", "job_title", "employee_id")
    extra = 0


class ProviderAdminProfileInline(admin.StackedInline):
    model = ProviderAdminProfile
    can_delete = False
    verbose_name_plural = "Provider Admin Profile"
    fk_name = "user"
    fields = (
        "profile_photo", "phone",
        "company_name", "company_registration_number", "company_logo",
        "company_website", "office_address", "office_phone", "tin_number",
        "whatsapp_number", "facebook_page", "instagram_handle",
        "is_verified", "verified_at",
        "average_rating", "total_reviews", "total_transactions",
    )
    readonly_fields = ("average_rating", "total_reviews", "total_transactions", "verified_at")
    extra = 0


class AdminProfileInline(admin.StackedInline):
    model = AdminProfile
    can_delete = False
    verbose_name_plural = "Admin Profile"
    fk_name = "user"
    fields = (
        "can_create_users", "can_verify_profiles",
        "can_manage_drivers", "can_manage_providers",
        "can_manage_payments", "can_manage_staff",
    )
    extra = 0

# ROLE → INLINE MAPPING
ROLE_INLINE_MAP = {
    "client":        ClientProfileInline,
    "driver":        DriverProfileInline,
    "staff":         StaffProfileInline,
    "provider_admin": ProviderAdminProfileInline,
    "admin":         AdminProfileInline,
}

# CUSTOM USER ADMIN
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display  = ("email", "full_name", "role", "is_active", "is_staff", "created_at")
    list_filter   = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering      = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (_("Role"), {"fields": ("role",)}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "password1", "password2", "is_active"),
        }),
    )

    readonly_fields = ("created_at", "updated_at", "last_login")

    def get_inlines(self, request, obj=None):
        """Dynamically show only the inline relevant to the user's role."""
        if obj and obj.role in ROLE_INLINE_MAP:
            return [ROLE_INLINE_MAP[obj.role]]
        return []

    def full_name(self, obj):
        return obj.get_full_name_or_email()
    full_name.short_description = "Full Name"

# STANDALONE PROFILE ADMINS
@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "license_number", "vehicle_plate", "is_available", "is_verified", "average_rating")
    list_filter   = ("is_verified", "is_available")
    search_fields = ("user__email", "user__first_name", "license_number", "vehicle_plate")
    readonly_fields = ("average_rating", "total_reviews", "total_trips", "verified_at")


@admin.register(ProviderAdminProfile)
class ProviderAdminProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "company_name", "is_verified", "average_rating", "total_transactions")
    list_filter   = ("is_verified",)
    search_fields = ("user__email", "company_name", "tin_number")
    readonly_fields = ("average_rating", "total_reviews", "total_transactions", "verified_at")


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "phone", "date_of_birth")
    search_fields = ("user__email", "user__first_name", "phone")


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "department", "job_title", "employee_id")
    search_fields = ("user__email", "employee_id", "department")


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display  = ("user", "can_create_users", "can_verify_profiles", "can_manage_drivers")
    search_fields = ("user__email",)