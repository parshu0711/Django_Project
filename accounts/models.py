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
