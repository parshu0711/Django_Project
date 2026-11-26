from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Platform user. HQ staff see every station; station staff see only their own."""

    class Role(models.TextChoices):
        HQ_ADMIN = "HQ_ADMIN", "HQ Administrator (NCPOR)"
        STATION_LEADER = "STATION_LEADER", "Station Leader"
        SCIENTIST = "SCIENTIST", "Scientist"
        ENGINEER = "ENGINEER", "Engineer / Technician"
        MEDICAL = "MEDICAL", "Medical Officer"
        LOGISTICS = "LOGISTICS", "Logistics Officer"
        SENSOR = "SENSOR", "Sensor / gateway (API only)"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.SCIENTIST)
    station = models.ForeignKey(
        "stations.Station",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff",
        help_text="Leave empty for HQ staff who oversee all stations.",
    )
    phone = models.CharField("phone / sat-phone", max_length=30, blank=True)
    pending_approval = models.BooleanField(
        default=False,
        help_text="Created through the sign-up page and waiting for HQ to approve it. Stays inactive until then.",
    )

    # Roles a person may request on the sign-up page. HQ administrator and sensor accounts are
    # only ever created by HQ, so they can't be self-assigned.
    SIGNUP_ROLES = (Role.STATION_LEADER, Role.SCIENTIST, Role.ENGINEER, Role.MEDICAL, Role.LOGISTICS)

    class Meta:
        ordering = ["first_name", "last_name"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_hq(self):
        return self.is_superuser or self.role == self.Role.HQ_ADMIN

    @property
    def can_manage(self):
        return self.is_hq or self.role == self.Role.STATION_LEADER

    @property
    def is_sensor(self):
        """Machine account for a station gateway: may only upload telemetry through the API."""
        return self.role == self.Role.SENSOR and not self.is_superuser

    @property
    def can_view_medical(self):
        """Medical records are confidential: HQ, station leaders and medical officers only."""
        return self.is_hq or self.role in (self.Role.STATION_LEADER, self.Role.MEDICAL)
