from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Project(models.Model):
    class Discipline(models.TextChoices):
        GLACIOLOGY = "GLACIOLOGY", "Glaciology"
        ATMOSPHERIC = "ATMOSPHERIC", "Atmospheric science & meteorology"
        GEOLOGY = "GEOLOGY", "Geology & geophysics"
        BIOLOGY = "BIOLOGY", "Biology & ecology"
        OCEANOGRAPHY = "OCEANOGRAPHY", "Oceanography"
        SPACE = "SPACE", "Upper atmosphere & space weather"
        HUMAN = "HUMAN", "Human physiology & medicine"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PROPOSED = "PROPOSED", "Proposed"
        ACTIVE = "ACTIVE", "Active"
        ON_HOLD = "ON_HOLD", "On hold"
        COMPLETED = "COMPLETED", "Completed"

    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    station = models.ForeignKey("stations.Station", on_delete=models.CASCADE, related_name="projects")
    expedition = models.ForeignKey(
        "personnel.Expedition", on_delete=models.SET_NULL, null=True, blank=True, related_name="projects"
    )
    discipline = models.CharField(max_length=12, choices=Discipline.choices, default=Discipline.OTHER)
    principal_investigator = models.CharField(max_length=120)
    institution = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    objectives = models.TextField(blank=True)

    class Meta:
        ordering = ["status", "title"]
        verbose_name = "research project"

    def __str__(self):
        return f"{self.code} – {self.title}"

    def get_absolute_url(self):
        return reverse("research:project_detail", args=[self.pk])


class FieldLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="logs")
    log_date = models.DateField(default=timezone.localdate)
    location = models.CharField(max_length=150, blank=True)
    activity = models.TextField()
    data_collected = models.TextField("samples / data collected", blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="field_logs"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-log_date", "-created_at"]
        verbose_name = "field log"

    def __str__(self):
        return f"{self.project.code} log {self.log_date:%d %b %Y}"

    def get_absolute_url(self):
        return reverse("research:log_detail", args=[self.pk])
