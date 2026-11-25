"""Template helpers and the management commands."""
import datetime
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.templatetags import polar_tags as t
from core.testing import PolarFixtures
from operations.models import Incident
from stations.models import Station
from telemetry.models import PowerReading, WeatherReading


class TemplateTagTests(TestCase):
    def test_badge_colours(self):
        self.assertEqual(t.badge_colour("CRITICAL"), "danger")
        self.assertEqual(t.badge_colour("RESOLVED"), "success")
        self.assertEqual(t.badge_colour("LOW"), "danger")               # low stock is bad
        self.assertEqual(t.badge_colour("LOW", "severity"), "secondary")  # low severity is not
        self.assertEqual(t.badge_colour("SOMETHING_NEW"), "secondary")

    def test_format_value(self):
        self.assertEqual(t.format_value(None), "—")
        self.assertEqual(t.format_value(True), "Yes")
        self.assertEqual(t.format_value(Decimal("1500.50")), "1,500.5")
        self.assertEqual(t.format_value(Decimal("20.00")), "20")
        self.assertEqual(t.format_value(3.14159), "3.1")
        self.assertEqual(t.format_value(datetime.date(2026, 1, 5)), "05 Jan 2026")

    def test_ago(self):
        now = timezone.now()
        self.assertEqual(t.ago(None), "never")
        self.assertEqual(t.ago(now), "just now")
        self.assertEqual(t.ago(now - timedelta(minutes=5)), "5 min ago")
        self.assertEqual(t.ago(now - timedelta(hours=3)), "3 h ago")
        self.assertEqual(t.ago(now - timedelta(days=4)), "4 days ago")

    def test_pct_class_and_wind_dir(self):
        self.assertEqual(t.pct_class(10), "danger")
        self.assertEqual(t.pct_class(35), "warning")
        self.assertEqual(t.pct_class(80), "success")
        self.assertEqual(t.pct_class("n/a"), "secondary")
        self.assertEqual(t.wind_dir(0), "N")
        self.assertEqual(t.wind_dir(135), "SE")
        self.assertEqual(t.wind_dir(350), "N")


class SimulateTelemetryCommandTests(PolarFixtures, TestCase):
    def test_creates_readings_for_active_stations_only(self):
        call_command("simulate_telemetry", stdout=StringIO())
        self.assertEqual(set(WeatherReading.objects.values_list("station__code", flat=True)), {"MAI", "BHA"})
        self.assertEqual(PowerReading.objects.count(), 2)

    def test_storm_option_triggers_blizzard_alert(self):
        call_command("simulate_telemetry", storm="mai", stdout=StringIO())
        alert = Incident.objects.get(station=self.mai, title="Blizzard / high-wind warning")
        self.assertTrue(alert.auto_generated)
        self.assertFalse(Incident.objects.filter(station=self.bha, auto_generated=True).exists())


class SeedDemoCommandTests(TestCase):
    def test_seed_loads_demo_and_is_idempotent(self):
        out = StringIO()
        call_command("seed_demo", stdout=out)
        self.assertEqual(set(Station.objects.values_list("code", flat=True)), {"MAI", "BHA", "DKG"})
        User = get_user_model()
        self.assertTrue(User.objects.get(username="hq_admin").is_hq)
        self.assertEqual(User.objects.get(username="maitri_leader").station.code, "MAI")
        self.assertIn("sensor_maitri", out.getvalue())

        out = StringIO()
        call_command("seed_demo", stdout=out)
        self.assertIn("already present", out.getvalue())
        self.assertEqual(Station.objects.count(), 3)

    def test_reset_reloads(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", reset=True, stdout=StringIO())
        self.assertEqual(Station.objects.count(), 3)
        self.assertEqual(get_user_model().objects.filter(username="hq_admin").count(), 1)


class SystemCheckTests(TestCase):
    def test_demo_mode_without_debug_is_an_error(self):
        from django.test import override_settings

        from core.checks import demo_mode_check
        with override_settings(DEMO_MODE=True, DEBUG=False, TESTING=False):
            self.assertEqual([e.id for e in demo_mode_check(None)], ["polarops.E001"])
        with override_settings(DEMO_MODE=False, DEBUG=False, TESTING=False):
            self.assertEqual(demo_mode_check(None), [])
        with override_settings(DEMO_MODE=True, DEBUG=True, TESTING=False):
            self.assertEqual(demo_mode_check(None), [])

    def test_station_codes_are_stored_upper_case(self):
        station = Station.objects.create(name="Himadri", code=" him ", latitude=78.9, longitude=11.9)
        self.assertEqual(station.code, "HIM")

    def test_seeded_sensor_accounts_are_sensors(self):
        call_command("seed_demo", stdout=StringIO())
        sensor = get_user_model().objects.get(username="sensor_maitri")
        self.assertTrue(sensor.is_sensor)
        self.assertFalse(sensor.has_usable_password())
