# apps/bookings/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse

from .models import Booking, BookingStatus, BookingStatusLog
from .services import BookingService


# ------------------------------------------------------------------
# Inline: status log
# ------------------------------------------------------------------
class BookingStatusLogInline(admin.TabularInline):
    model = BookingStatusLog
    extra = 0
    readonly_fields = ["from_status", "to_status", "changed_by", "note", "changed_at"]
    can_delete = False
    ordering = ["changed_at"]

    def has_add_permission(self, request, obj=None):
        return False



# Main Booking admin

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        "reference", "patient_name", "emergency_type_badge",
        "status_badge", "payment_status", "client_link",
        "ambulance", "created_at",
    ]
    list_filter = [
        "status", "emergency_type", "payment_method", "payment_status",
        "created_at", "is_deleted",
    ]
    search_fields = [
        "reference", "patient_name", "patient_phone",
        "pickup_address", "client__email", "client__first_name",
    ]
    readonly_fields = [
        "id", "reference", "total_fare",
        "created_at", "confirmed_at", "dispatched_at",
        "ongoing_at", "arrived_at", "completed_at",
        "cancelled_at", "updated_at",
        "duration_display", "status_badge",
    ]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    inlines = [BookingStatusLogInline]
    save_on_top = True

    fieldsets = (
        ("Reference", {
            "fields": ("id", "reference"),
        }),
        ("Client & Patient", {
            "fields": (
                "client",
                ("patient_name", "patient_phone", "patient_age"),
                ("emergency_type", "notes"),
            ),
        }),
        ("Pickup Location", {
            "fields": (
                "pickup_address",
                ("pickup_lat", "pickup_lon"),
            ),
        }),
        ("Destination", {
            "classes": ("collapse",),
            "fields": (
                "destination_address",
                ("destination_lat", "destination_lon"),
            ),
        }),
        ("Resources", {
            "fields": ("ambulance", "hospital"),
        }),
        ("Status", {
            "fields": ("status", "status_badge", "cancellation_reason"),
        }),
        ("Payment", {
            "fields": (
                ("payment_method", "payment_status"),
                "insurance_provider", "insurance_policy_ref",
            ),
        }),
        ("Fare (UGX)", {
            "fields": (
                ("base_fare", "platform_fee", "discount"),
                "total_fare",
            ),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": (
                "created_at", "confirmed_at", "dispatched_at",
                "ongoing_at", "arrived_at", "completed_at",
                "cancelled_at", "updated_at", "duration_display",
            ),
        }),
        ("Flags", {
            "classes": ("collapse",),
            "fields": ("is_deleted",),
        }),
    )

    actions = [
        "action_confirm",
        "action_dispatch",
        "action_complete",
        "action_cancel",
        "action_restore",
    ]

    
    # Custom display columns
    
    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            BookingStatus.PENDING:    "#f59e0b",
            BookingStatus.CONFIRMED:  "#3b82f6",
            BookingStatus.DISPATCHED: "#8b5cf6",
            BookingStatus.ONGOING:    "#6366f1",
            BookingStatus.ARRIVED:    "#0ea5e9",
            BookingStatus.COMPLETED:  "#10b981",
            BookingStatus.CANCELLED:  "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.display(description="Emergency")
    def emergency_type_badge(self, obj):
        return obj.get_emergency_type_display()

    @admin.display(description="Client")
    def client_link(self, obj):
        if obj.client:
            url = reverse("admin:auth_user_change", args=[obj.client.pk])
            return format_html('<a href="{}">{}</a>', url, obj.client.get_full_name() or obj.client.email)
        return "—"

    @admin.display(description="Duration")
    def duration_display(self, obj):
        mins = obj.duration_minutes
        if mins is None:
            return "—"
        return f"{mins} min"

    
    # Bulk actions
  
    def _bulk_transition(self, request, queryset, method_name, label):
        success, errors = 0, []
        for booking in queryset:
            try:
                getattr(BookingService, method_name)(booking, operator=request.user)
                success += 1
            except Exception as e:
                errors.append(f"{booking.reference}: {e}")
        if success:
            self.message_user(request, f"{success} booking(s) {label}.")
        for err in errors:
            self.message_user(request, err, level="error")

    @admin.action(description="✅ Confirm selected bookings")
    def action_confirm(self, request, queryset):
        self._bulk_transition(request, queryset, "confirm", "confirmed")

    @admin.action(description="🚑 Dispatch selected bookings")
    def action_dispatch(self, request, queryset):
        self._bulk_transition(request, queryset, "dispatch", "dispatched")

    @admin.action(description="✔ Complete selected bookings")
    def action_complete(self, request, queryset):
        self._bulk_transition(request, queryset, "complete", "completed")

    @admin.action(description="✖ Cancel selected bookings")
    def action_cancel(self, request, queryset):
        success, errors = 0, []
        for booking in queryset:
            try:
                BookingService.cancel(booking, cancelled_by=request.user, reason="Bulk cancelled via admin.")
                success += 1
            except Exception as e:
                errors.append(f"{booking.reference}: {e}")
        if success:
            self.message_user(request, f"{success} booking(s) cancelled.")
        for err in errors:
            self.message_user(request, err, level="error")

    @admin.action(description="♻️ Restore (un-delete) selected bookings")
    def action_restore(self, request, queryset):
        updated = queryset.update(is_deleted=False)
        self.message_user(request, f"{updated} booking(s) restored.")

    def get_queryset(self, request):
        # Show soft-deleted records in admin (staff can restore them)
        return super().get_queryset(request)



# Status log read-only admin (useful for audits)

@admin.register(BookingStatusLog)
class BookingStatusLogAdmin(admin.ModelAdmin):
    list_display = ["booking", "from_status", "to_status", "changed_by", "changed_at"]
    list_filter  = ["to_status", "changed_at"]
    search_fields = ["booking__reference", "changed_by__email", "note"]
    readonly_fields = ["booking", "from_status", "to_status", "changed_by", "note", "changed_at"]
    ordering = ["-changed_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser