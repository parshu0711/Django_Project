from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Station(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active (year-round)"
        SEASONAL = "SEASONAL", "Seasonal (summer only)"
        INACTIVE = "INACTIVE", "Decommissioned / supply base"

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text="Short code used by sensors and the API, e.g. MAI")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    region = models.CharField(max_length=150, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    established = models.PositiveSmallIntegerField("year established", null=True, blank=True)
    capacity_winter = models.PositiveSmallIntegerField("winter capacity", default=0)
    capacity_summer = models.PositiveSmallIntegerField("summer capacity", default=0)
    communications = models.CharField(max_length=150, blank=True, help_text="e.g. VSAT, INMARSAT, HF radio")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("stations:station_detail", args=[self.pk])

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()   # sensors and the API look stations up by code
        super().save(*args, **kwargs)

    @property
    def latest_weather(self):
        return self.weather_readings.order_by("-recorded_at").first()

    @property
    def latest_power(self):
        return self.power_readings.order_by("-recorded_at").first()


class SitRep(models.Model):
    """Daily situation report sent from a station to HQ."""

    class Status(models.TextChoices):
        GREEN = "GREEN", "Green"
        AMBER = "AMBER", "Amber"
        RED = "RED", "Red"

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="sitreps")
    report_date = models.DateField(default=timezone.localdate)
    overall_status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.GREEN,
        help_text="Green = normal, Amber = degraded / caution, Red = emergency",
    )
    personnel_on_station = models.PositiveSmallIntegerField(default=0)
    weather_summary = models.CharField(max_length=255, blank=True)
    activities = models.TextField("activities carried out")
    issues = models.TextField("issues / concerns", blank=True)
    requests_to_hq = models.TextField("requests to HQ", blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="sitreps"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-report_date", "-created_at"]
        verbose_name = "situation report"

    def __str__(self):
        return f"{self.station.code} SITREP {self.report_date:%d %b %Y}"

    def get_absolute_url(self):
        return reverse("stations:sitrep_detail", args=[self.pk])
