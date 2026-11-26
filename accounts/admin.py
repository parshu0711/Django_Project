from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "role", "station", "email", "is_active", "pending_approval")
    list_filter = ("pending_approval", "role", "station", "is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Station assignment", {"fields": ("role", "station", "phone", "pending_approval")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Station assignment", {"fields": ("first_name", "last_name", "email", "role", "station")}),
    )
    actions = ["approve_signups"]

    @admin.action(description="Approve selected account requests")
    def approve_signups(self, request, queryset):
        count = queryset.filter(pending_approval=True).update(is_active=True, pending_approval=False)
        self.message_user(request, f"Approved {count} account request(s).", messages.SUCCESS)
