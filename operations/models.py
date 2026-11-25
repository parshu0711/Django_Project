from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone


class Equipment(models.Model):
    class Kind(models.TextChoices):
        GENERATOR = "GENERATOR", "Power generator"
        RENEWABLE = "RENEWABLE", "Solar / wind system"
        VEHICLE = "VEHICLE", "Vehicle / snow-cat"
        COMMS = "COMMS", "Communication"
        HVAC = "HVAC", "Heating & ventilation"
        WATER = "WATER", "Water / desalination"
        SCIENTIFIC = "SCIENTIFIC", "Scientific instrument"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        OPERATIONAL = "OPERATIONAL", "Operational"
        STANDBY = "STANDBY", "Standby"
        MAINTENANCE = "MAINTENANCE", "Under maintenance"
        FAULTY = "FAULTY", "Faulty"

    station = models.ForeignKey("stations.Station", on_delete=models.CASCADE, related_name="equipment")
    name = models.CharField(max_length=120)
    kind = models.CharField("type", max_length=12, choices=Kind.choices, default=Kind.OTHER)
    serial_number = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPERATIONAL)
    commissioned_on = models.DateField(null=True, blank=True)
    last_serviced_on = models.DateField(null=True, blank=True)
    service_interval_days = models.PositiveSmallIntegerField(default=90)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["station__name", "kind", "name"]
        verbose_name_plural = "equipment"

    def __str__(self):
        return f"{self.name} ({self.station.code})"

    def get_absolute_url(self):
        return reverse("operations:equipment_detail", args=[self.pk])

    @property
    def next_service_due(self):
        if self.last_serviced_on and self.service_interval_days:
            return self.last_serviced_on + timedelta(days=self.service_interval_days)
        return None

    @property
    def service_state(self):
        due = self.next_service_due
        if not due:
            return "UNKNOWN"
        today = timezone.localdate()
        if due < today:
            return "OVERDUE"
        if due <= today + timedelta(days=14):
            return "DUE_SOON"
        return "OK"


class MaintenanceTask(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        DONE = "DONE", "Done"

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    due_date = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_tasks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-status", "due_date"]  # OPEN, IN_PROGRESS, DONE
        verbose_name = "maintenance task"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("operations:task_detail", args=[self.pk])

    def save(self, *args, **kwargs):
        just_completed = self.status == self.Status.DONE and not self.completed_at
        if just_completed:
            self.completed_at = timezone.now()
        elif self.status != self.Status.DONE:
            self.completed_at = None
        with transaction.atomic():
            super().save(*args, **kwargs)
            if just_completed:
                # completing a task counts as a service of the equipment
                Equipment.objects.filter(pk=self.equipment_id).update(last_serviced_on=timezone.localdate())


class Incident(models.Model):
    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Category(models.TextChoices):
        MEDICAL = "MEDICAL", "Medical"
        EQUIPMENT = "EQUIPMENT", "Equipment / power"
        WEATHER = "WEATHER", "Weather"
        SAFETY = "SAFETY", "Safety / fire"
        COMMS = "COMMS", "Communication loss"
        ENVIRONMENT = "ENVIRONMENT", "Environmental (spill / waste)"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged by HQ"
        RESOLVED = "RESOLVED", "Resolved"

    station = models.ForeignKey("stations.Station", on_delete=models.CASCADE, related_name="incidents")
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=12, choices=Category.choices, default=Category.OTHER)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    description = models.TextField()
    action_taken = models.TextField(blank=True)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidents_reported"
    )
    reported_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    auto_generated = models.BooleanField(default=False, help_text="Raised automatically from sensor data")

    class Meta:
        ordering = ["-reported_at"]
        verbose_name = "incident / alert"
        verbose_name_plural = "incidents & alerts"

    def __str__(self):
        return f"{self.station.code}: {self.title}"

    def get_absolute_url(self):
        return reverse("operations:incident_detail", args=[self.pk])

    def save(self, *args, **kwargs):
        if self.status == self.Status.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status != self.Status.RESOLVED:
            self.resolved_at = None
        super().save(*args, **kwargs)
