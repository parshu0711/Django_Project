from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Expedition(models.Model):
    """An Indian Scientific Expedition to Antarctica (ISEA) batch."""

    code = models.CharField(max_length=20, unique=True, help_text="e.g. ISEA-45")
    name = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    leader = models.CharField("expedition leader", max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.code

    def get_absolute_url(self):
        return reverse("personnel:expedition_detail", args=[self.pk])


class Member(models.Model):
    class Status(models.TextChoices):
        ON_STATION = "ON_STATION", "On station"
        ON_FIELD = "ON_FIELD", "On field trip"
        IN_TRANSIT = "IN_TRANSIT", "In transit"
        DEPARTED = "DEPARTED", "Departed"

    class Team(models.TextChoices):
        WINTER = "WINTER", "Wintering team"
        SUMMER = "SUMMER", "Summer team"

    class BloodGroup(models.TextChoices):
        A_POS = "A+", "A+"
        A_NEG = "A-", "A-"
        B_POS = "B+", "B+"
        B_NEG = "B-", "B-"
        O_POS = "O+", "O+"
        O_NEG = "O-", "O-"
        AB_POS = "AB+", "AB+"
        AB_NEG = "AB-", "AB-"

    full_name = models.CharField(max_length=120)
    station = models.ForeignKey("stations.Station", on_delete=models.PROTECT, related_name="members")
    expedition = models.ForeignKey(Expedition, on_delete=models.SET_NULL, null=True, blank=True, related_name="members")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="member_profile"
    )
    designation = models.CharField(max_length=100)
    organisation = models.CharField(max_length=100, blank=True, help_text="e.g. NCPOR, IMD, GSI, Indian Army")
    team = models.CharField(max_length=10, choices=Team.choices, default=Team.WINTER)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ON_STATION)
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices, blank=True)
    emergency_contact = models.CharField(max_length=150, blank=True)
    arrival_date = models.DateField(null=True, blank=True)
    departure_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name = "expedition member"

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("personnel:member_detail", args=[self.pk])


class MedicalCheck(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="medical_checks")
    checked_on = models.DateField(default=timezone.localdate)
    examiner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="medical_checks"
    )
    bp_systolic = models.PositiveSmallIntegerField("BP systolic", null=True, blank=True)
    bp_diastolic = models.PositiveSmallIntegerField("BP diastolic", null=True, blank=True)
    pulse = models.PositiveSmallIntegerField("pulse (bpm)", null=True, blank=True)
    spo2 = models.PositiveSmallIntegerField("SpO2 (%)", null=True, blank=True)
    temperature_c = models.DecimalField("body temp (°C)", max_digits=4, decimal_places=1, null=True, blank=True)
    weight_kg = models.DecimalField("weight (kg)", max_digits=5, decimal_places=1, null=True, blank=True)
    fit_for_duty = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-checked_on"]
        verbose_name = "medical check"

    def __str__(self):
        return f"{self.member} – {self.checked_on:%d %b %Y}"

    def get_absolute_url(self):
        return reverse("personnel:medical_detail", args=[self.pk])

    @property
    def blood_pressure(self):
        if self.bp_systolic and self.bp_diastolic:
            return f"{self.bp_systolic}/{self.bp_diastolic}"
        return ""
