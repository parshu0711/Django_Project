from django.contrib import admin

from .models import Equipment, Incident, MaintenanceTask


class TaskInline(admin.TabularInline):
    model = MaintenanceTask
    fields = ("title", "priority", "status", "due_date", "assigned_to")
    extra = 0


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "station", "kind", "status", "last_serviced_on", "next_service_due")
    list_filter = ("station", "kind", "status")
    search_fields = ("name", "serial_number")
    inlines = [TaskInline]


@admin.register(MaintenanceTask)
class MaintenanceTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "equipment", "priority", "status", "due_date", "assigned_to")
    list_filter = ("priority", "status", "equipment__station")


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "station", "category", "severity", "status", "reported_at", "auto_generated")
    list_filter = ("station", "category", "severity", "status", "auto_generated")
    search_fields = ("title", "description")
    date_hierarchy = "reported_at"
