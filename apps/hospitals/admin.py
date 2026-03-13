# apps/hospitals/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Avg

from .models import Hospital, HospitalReview, HospitalStatus
from .services import HospitalService, ReviewService


# ------------------------------------------------------------------
# Inline: reviews inside hospital
# ------------------------------------------------------------------
class HospitalReviewInline(admin.TabularInline):
    model         = HospitalReview
    extra         = 0
    readonly_fields = ["reviewer", "booking", "rating", "comment", "is_approved", "created_at"]
    fields        = ["reviewer", "rating", "comment", "is_approved", "created_at"]
    can_delete    = True
    ordering      = ["-created_at"]
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------
def _status_badge(status_value, label):
    colors = {
        HospitalStatus.ACTIVE:          "#10b981",
        HospitalStatus.INACTIVE:        "#6b7280",
        HospitalStatus.FULL:            "#ef4444",
        HospitalStatus.EMERGENCY_ONLY:  "#f59e0b",
    }
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 8px;'
        'border-radius:12px;font-size:11px;font-weight:600;">{}</span>',
        colors.get(status_value, "#6b7280"), label,
    )


# ------------------------------------------------------------------
# Hospital admin
# ------------------------------------------------------------------
@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display  = [
        "name", "hospital_type", "district", "status_badge",
        "verified_icon", "featured_icon", "available_beds",
        "rating", "review_count", "updated_at",
    ]
    list_filter   = [
        "status", "hospital_type", "district",
        "is_verified", "is_active", "is_featured",
        "has_icu", "has_maternity", "accepts_insurance", "is_24_hours",
    ]
    search_fields = ["name", "registration_no", "district", "admin_user__email", "phone_primary"]
    readonly_fields = [
        "id", "rating", "review_count",
        "bed_occupancy_display", "is_accepting_display",
        "created_at", "updated_at",
    ]
    ordering      = ["-is_featured", "-rating", "name"]
    inlines       = [HospitalReviewInline]
    save_on_top   = True
    actions       = [
        "action_verify", "action_deactivate",
        "action_feature", "action_unfeature",
    ]

    fieldsets = (
        ("Identity", {
            "fields": ("id", "admin_user", "name", "hospital_type", "registration_no", "description"),
        }),
        ("Contact", {
            "fields": ("phone_primary", "phone_emergency", "email", "website"),
        }),
        ("Location", {
            "fields": ("address", "district", ("latitude", "longitude")),
        }),
        ("Capabilities", {
            "fields": (
                "specialities",
                ("has_icu", "has_maternity", "has_blood_bank", "has_ambulance"),
                ("accepts_insurance", "is_24_hours"),
            ),
        }),
        ("Bed Availability", {
            "fields": (("total_beds", "available_beds"), "bed_occupancy_display"),
        }),
        ("Platform", {
            "fields": ("status", "is_verified", "is_active", "is_featured", "is_accepting_display"),
        }),
        ("Ratings", {
            "fields": ("rating", "review_count"),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )

    # ------------------------------------------------------------------
    # Display columns
    # ------------------------------------------------------------------
    @admin.display(description="Status")
    def status_badge(self, obj):
        return _status_badge(obj.status, obj.get_status_display())

    @admin.display(description="Verified", boolean=True)
    def verified_icon(self, obj):
        return obj.is_verified

    @admin.display(description="Featured", boolean=True)
    def featured_icon(self, obj):
        return obj.is_featured

    @admin.display(description="Occupancy")
    def bed_occupancy_display(self, obj):
        pct = obj.bed_occupancy_pct
        return f"{pct}%" if pct is not None else "—"

    @admin.display(description="Accepting Patients", boolean=True)
    def is_accepting_display(self, obj):
        return obj.is_accepting_patients

    # ------------------------------------------------------------------
    # Bulk actions
    # ------------------------------------------------------------------
    @admin.action(description="✅ Verify selected hospitals")
    def action_verify(self, request, queryset):
        for hospital in queryset:
            HospitalService.verify(hospital)
        self.message_user(request, f"{queryset.count()} hospital(s) verified.")

    @admin.action(description="🚫 Deactivate selected hospitals")
    def action_deactivate(self, request, queryset):
        for hospital in queryset:
            HospitalService.deactivate(hospital)
        self.message_user(request, f"{queryset.count()} hospital(s) deactivated.")

    @admin.action(description="⭐ Feature selected hospitals")
    def action_feature(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f"{queryset.count()} hospital(s) featured.")

    @admin.action(description="☆ Unfeature selected hospitals")
    def action_unfeature(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, f"{queryset.count()} hospital(s) unfeatured.")


# ------------------------------------------------------------------
# Review admin (moderation queue)
# ------------------------------------------------------------------
@admin.register(HospitalReview)
class HospitalReviewAdmin(admin.ModelAdmin):
    list_display  = ["hospital", "reviewer", "stars_display", "is_approved", "created_at"]
    list_filter   = ["is_approved", "rating", "created_at"]
    search_fields = ["hospital__name", "reviewer__email", "comment"]
    readonly_fields = ["id", "hospital", "reviewer", "booking", "rating", "comment", "created_at"]
    ordering      = ["-created_at"]
    actions       = ["action_approve", "action_reject"]

    @admin.display(description="Rating")
    def stars_display(self, obj):
        return "★" * obj.rating + "☆" * (5 - obj.rating)

    @admin.action(description="✅ Approve selected reviews")
    def action_approve(self, request, queryset):
        for review in queryset.filter(is_approved=False):
            ReviewService.approve_review(review)
        self.message_user(request, f"Reviews approved.")

    @admin.action(description="🗑 Reject (delete) selected reviews")
    def action_reject(self, request, queryset):
        for review in queryset:
            ReviewService.reject_review(review)
        self.message_user(request, "Reviews rejected and deleted.")

    def has_add_permission(self, request):
        return False