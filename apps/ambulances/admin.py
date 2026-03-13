# apps/ambulances/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import Ambulance, AmbulanceStatus, Provider


# ------------------------------------------------------------------
# Inline: ambulances inside a provider
# ------------------------------------------------------------------
class AmbulanceInline(admin.TabularInline):
    model = Ambulance
    extra = 0
    fields = [
        "plate_number", "ambulance_type", "status_badge_inline",
        "driver", "base_fare", "is_active",
    ]
    readonly_fields = ["status_badge_inline"]
    show_change_link = True

    @admin.display(description="Status")
    def status_badge_inline(self, obj):
        return _status_badge(obj.status, obj.get_status_display())


# ------------------------------------------------------------------
# Shared badge helper
# ------------------------------------------------------------------
def _status_badge(status_value, label):
    colors = {
        AmbulanceStatus.AVAILABLE:   "#10b981",
        AmbulanceStatus.BUSY:        "#f59e0b",
        AmbulanceStatus.MAINTENANCE: "#6366f1",
        AmbulanceStatus.OFFLINE:     "#6b7280",
    }
    color = colors.get(status_value, "#6b7280")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 8px;'
        'border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
        color, label,
    )


# ------------------------------------------------------------------
# Provider admin
# ------------------------------------------------------------------
@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display   = ["name", "district", "admin_user", "verified_badge", "is_active", "rating", "created_at"]
    list_filter    = ["is_verified", "is_active", "district"]
    search_fields  = ["name", "phone", "admin_user__email"]
    readonly_fields = ["id", "created_at", "rating"]
    ordering       = ["name"]
    inlines        = [AmbulanceInline]
    actions        = ["action_verify", "action_deactivate"]

    fieldsets = (
        ("Identity", {
            "fields": ("id", "name", "description", "admin_user"),
        }),
        ("Contact", {
            "fields": ("phone", "address", "district"),
        }),
        ("Status", {
            "fields": ("is_verified", "is_active", "rating", "created_at"),
        }),
    )

    @admin.display(description="Verified", boolean=True)
    def verified_badge(self, obj):
        return obj.is_verified

    @admin.action(description="✅ Verify selected providers")
    def action_verify(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f"{updated} provider(s) verified.")

    @admin.action(description="🚫 Deactivate selected providers")
    def action_deactivate(self, request, queryset):
        from .services import ProviderService
        for provider in queryset:
            ProviderService.deactivate_provider(provider)
        self.message_user(request, f"{queryset.count()} provider(s) deactivated.")


# ------------------------------------------------------------------
# Ambulance admin
# ------------------------------------------------------------------
@admin.register(Ambulance)
class AmbulanceAdmin(admin.ModelAdmin):
    list_display  = [
        "plate_number", "provider", "ambulance_type",
        "status_badge", "driver", "base_fare", "has_gps", "is_active", "updated_at",
    ]
    list_filter   = ["status", "ambulance_type", "is_active", "provider"]
    search_fields = ["plate_number", "provider__name", "driver__email", "vehicle_make"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering      = ["provider", "plate_number"]
    actions       = ["action_set_available", "action_set_offline", "action_set_maintenance"]

    fieldsets = (
        ("Identity", {
            "fields": ("id", "provider", "plate_number"),
        }),
        ("Vehicle", {
            "fields": (
                ("vehicle_make", "vehicle_model", "vehicle_year"),
                "ambulance_type",
            ),
        }),
        ("Operations", {
            "fields": ("status", "driver", "base_fare", "is_active"),
        }),
        ("GPS Location", {
            "classes": ("collapse",),
            "fields": (("latitude", "longitude"),),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )

    @admin.display(description="Status")
    def status_badge(self, obj):
        return _status_badge(obj.status, obj.get_status_display())

    @admin.display(description="GPS", boolean=True)
    def has_gps(self, obj):
        return obj.latitude is not None and obj.longitude is not None

    # Bulk status actions
    def _bulk_status(self, request, queryset, new_status, label):
        updated = queryset.update(status=new_status)
        self.message_user(request, f"{updated} ambulance(s) marked as {label}.")

    @admin.action(description="✅ Mark selected as Available")
    def action_set_available(self, request, queryset):
        self._bulk_status(request, queryset, AmbulanceStatus.AVAILABLE, "available")

    @admin.action(description="📴 Mark selected as Offline")
    def action_set_offline(self, request, queryset):
        self._bulk_status(request, queryset, AmbulanceStatus.OFFLINE, "offline")

    @admin.action(description="🔧 Mark selected as Under Maintenance")
    def action_set_maintenance(self, request, queryset):
        self._bulk_status(request, queryset, AmbulanceStatus.MAINTENANCE, "under maintenance")