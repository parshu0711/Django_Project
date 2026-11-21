from django.contrib import admin

from .models import FieldLog, Project


class FieldLogInline(admin.TabularInline):
    model = FieldLog
    fields = ("log_date", "location", "activity", "author")
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "station", "discipline", "principal_investigator", "status")
    list_filter = ("station", "discipline", "status")
    search_fields = ("code", "title", "principal_investigator", "institution")
    inlines = [FieldLogInline]


@admin.register(FieldLog)
class FieldLogAdmin(admin.ModelAdmin):
    list_display = ("log_date", "project", "location", "author")
    list_filter = ("project__station",)
