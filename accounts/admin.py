from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "role", "station", "email", "is_active")
    list_filter = ("role", "station", "is_active", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (("Station assignment", {"fields": ("role", "station", "phone")}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Station assignment", {"fields": ("first_name", "last_name", "email", "role", "station")}),
    )
