from django.contrib import admin

from .models import Expedition, MedicalCheck, Member


class MemberInline(admin.TabularInline):
    model = Member
    fields = ("full_name", "station", "designation", "team", "status")
    extra = 0


@admin.register(Expedition)
class ExpeditionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "start_date", "end_date", "leader")
    inlines = [MemberInline]


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "station", "expedition", "designation", "team", "status", "blood_group")
    list_filter = ("station", "expedition", "team", "status")
    search_fields = ("full_name", "designation", "organisation")


@admin.register(MedicalCheck)
class MedicalCheckAdmin(admin.ModelAdmin):
    list_display = ("member", "checked_on", "blood_pressure", "pulse", "spo2", "fit_for_duty")
    list_filter = ("fit_for_duty", "member__station")
    date_hierarchy = "checked_on"
