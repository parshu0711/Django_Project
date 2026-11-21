from django.contrib import admin

from .models import SitRep, Station


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "status", "region", "established", "capacity_winter", "capacity_summer")
    list_filter = ("status",)
    search_fields = ("name", "code", "region")


@admin.register(SitRep)
class SitRepAdmin(admin.ModelAdmin):
    list_display = ("report_date", "station", "overall_status", "personnel_on_station", "author")
    list_filter = ("station", "overall_status")
    date_hierarchy = "report_date"
    search_fields = ("activities", "issues")
