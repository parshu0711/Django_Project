"""Shared fixtures for the PolarOps test suite."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from inventory.models import Item
from operations.models import Equipment, Incident
from personnel.models import Expedition, Member
from research.models import Project
from stations.models import Station

TEST_PASSWORD = "Ice-Shelf-2026!"


class PolarFixtures:
    """Mixin for TestCase: two active stations, one decommissioned, and a user for each role."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        User = get_user_model()
        cls.mai = Station.objects.create(name="Maitri", code="MAI", latitude=-70.7667, longitude=11.7333,
                                         region="Schirmacher Oasis", established=1989)
        cls.bha = Station.objects.create(name="Bharati", code="BHA", latitude=-69.4083, longitude=76.1872,
                                         region="Larsemann Hills", established=2012)
        cls.dkg = Station.objects.create(name="Dakshin Gangotri", code="DKG", latitude=-70.08, longitude=12.0,
                                         status=Station.Status.INACTIVE, established=1983)

        def user(username, role, station=None, email="", **extra):
            return User.objects.create_user(username=username, password=TEST_PASSWORD, role=role,
                                            station=station, email=email, first_name=username.title(), **extra)

        R = User.Role
        cls.hq = user("hq", R.HQ_ADMIN, email="hq@example.org")
        cls.mai_leader = user("mai_leader", R.STATION_LEADER, cls.mai, email="leader@maitri.example.org")
        cls.bha_leader = user("bha_leader", R.STATION_LEADER, cls.bha, email="leader@bharati.example.org")
        cls.mai_scientist = user("mai_scientist", R.SCIENTIST, cls.mai, email="sci@maitri.example.org")
        cls.bha_engineer = user("bha_engineer", R.ENGINEER, cls.bha)
        cls.unassigned = user("unassigned", R.SCIENTIST)
        cls.mai_sensor = user("mai_sensor", R.SENSOR, cls.mai)
        cls.mai_token = Token.objects.create(user=cls.mai_sensor)

        cls.expedition = Expedition.objects.create(code="ISEA-45", name="45th expedition", start_date=date(2025, 11, 1))
        cls.mai_member = Member.objects.create(full_name="Ravi Kumar", station=cls.mai, designation="Station doctor",
                                               expedition=cls.expedition)
        cls.bha_member = Member.objects.create(full_name="Priya Shah", station=cls.bha, designation="Engineer",
                                               expedition=cls.expedition)

        cls.mai_diesel = Item.objects.create(station=cls.mai, name="Arctic diesel", category=Item.Category.FUEL,
                                             unit="litres", quantity=Decimal("500"), min_threshold=Decimal("100"))
        cls.bha_rice = Item.objects.create(station=cls.bha, name="Rice", category=Item.Category.FOOD, unit="kg",
                                           quantity=Decimal("5"), min_threshold=Decimal("50"))   # low stock

        cls.mai_generator = Equipment.objects.create(station=cls.mai, name="DG set 1", kind=Equipment.Kind.GENERATOR)
        cls.bha_generator = Equipment.objects.create(station=cls.bha, name="DG set A", kind=Equipment.Kind.GENERATOR)

        cls.mai_project = Project.objects.create(code="GLAC-1", title="Ice core study", station=cls.mai,
                                                 principal_investigator="Dr. Rao")
        cls.bha_project = Project.objects.create(code="ATM-2", title="Aurora watch", station=cls.bha,
                                                 principal_investigator="Dr. Iyer")

        cls.bha_incident = Incident.objects.create(station=cls.bha, title="Generator trip", description="Tripped",
                                                   severity=Incident.Severity.LOW)

    def login(self, user):
        self.client.force_login(user)
        return user
