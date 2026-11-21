"""Automatic alert rules (telemetry/alerts.py) fired from sensor readings."""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from core.testing import PolarFixtures
from operations.models import Incident

from .models import PowerReading, WeatherReading

ALERTS = {"WIND_KMH": 100, "TEMP_C": -45, "VISIBILITY_KM": 0.2, "FUEL_PCT": 20, "BATTERY_PCT": 15, "DEDUPE_HOURS": 6}


def weather(station, **kw):
    values = {"temperature_c": -10, "wind_speed_kmh": 20, "pressure_hpa": 985, "visibility_km": 10, **kw}
    return WeatherReading.objects.create(station=station, **values)


def power(station, **kw):
    return PowerReading.objects.create(station=station, **{"fuel_level_pct": 70, "battery_pct": 80, **kw})


@override_settings(POLAROPS_ALERTS=ALERTS)
class WeatherAlertTests(PolarFixtures, TestCase):
    def auto(self, title):
        return Incident.objects.filter(station=self.mai, auto_generated=True, title=title)

    def test_calm_weather_raises_nothing(self):
        weather(self.mai)
        self.assertFalse(Incident.objects.filter(auto_generated=True).exists())

    def test_high_wind_is_high_severity(self):
        weather(self.mai, wind_speed_kmh=100)
        self.assertEqual(self.auto("Blizzard / high-wind warning").get().severity, Incident.Severity.HIGH)

    def test_very_high_wind_is_critical(self):
        weather(self.mai, wind_speed_kmh=150)
        self.assertEqual(self.auto("Blizzard / high-wind warning").get().severity, Incident.Severity.CRITICAL)

    def test_extreme_cold(self):
        weather(self.mai, temperature_c=-45)
        self.assertTrue(self.auto("Extreme cold warning").exists())

    def test_whiteout(self):
        weather(self.mai, visibility_km=0.1)
        self.assertTrue(self.auto("Whiteout conditions").exists())

    def test_missing_visibility_is_not_a_whiteout(self):
        weather(self.mai, visibility_km=None)
        self.assertFalse(self.auto("Whiteout conditions").exists())

    def test_duplicates_are_suppressed_within_window(self):
        for _ in range(3):
            weather(self.mai, wind_speed_kmh=120)
        self.assertEqual(self.auto("Blizzard / high-wind warning").count(), 1)

    def test_same_alert_at_another_station_is_separate(self):
        weather(self.mai, wind_speed_kmh=120)
        weather(self.bha, wind_speed_kmh=120)
        self.assertEqual(Incident.objects.filter(auto_generated=True).count(), 2)

    def test_new_alert_after_previous_one_resolved(self):
        weather(self.mai, wind_speed_kmh=120)
        self.auto("Blizzard / high-wind warning").update(status=Incident.Status.RESOLVED)
        weather(self.mai, wind_speed_kmh=120)
        self.assertEqual(self.auto("Blizzard / high-wind warning").count(), 2)

    def test_new_alert_after_dedupe_window(self):
        weather(self.mai, wind_speed_kmh=120)
        self.auto("Blizzard / high-wind warning").update(reported_at=timezone.now() - timedelta(hours=7))
        weather(self.mai, wind_speed_kmh=120)
        self.assertEqual(self.auto("Blizzard / high-wind warning").count(), 2)

    def test_editing_a_reading_does_not_alert(self):
        reading = weather(self.mai)
        reading.wind_speed_kmh = 200
        reading.save()
        self.assertFalse(Incident.objects.filter(auto_generated=True).exists())

    @override_settings(POLAROPS_ALERTS={**ALERTS, "WIND_KMH": 60})
    def test_thresholds_come_from_settings(self):
        weather(self.mai, wind_speed_kmh=70)
        self.assertTrue(self.auto("Blizzard / high-wind warning").exists())


@override_settings(POLAROPS_ALERTS=ALERTS)
class PowerAlertTests(PolarFixtures, TestCase):
    def test_low_fuel_high_then_critical(self):
        power(self.mai, fuel_level_pct=18)
        self.assertEqual(Incident.objects.get(title="Low fuel reserve").severity, Incident.Severity.HIGH)
        power(self.bha, fuel_level_pct=9)
        self.assertEqual(Incident.objects.get(station=self.bha, title="Low fuel reserve").severity,
                         Incident.Severity.CRITICAL)

    def test_low_battery(self):
        power(self.mai, battery_pct=10)
        self.assertTrue(Incident.objects.filter(title="Battery bank critically low").exists())

    def test_healthy_power_raises_nothing(self):
        power(self.mai, battery_pct=None)
        self.assertFalse(Incident.objects.filter(auto_generated=True).exists())


class PowerReadingModelTests(PolarFixtures, TestCase):
    def test_renewable_share(self):
        reading = PowerReading(station=self.mai, generator_kw=60, solar_kw=30, wind_kw=10, fuel_level_pct=50)
        self.assertEqual(reading.total_generation_kw, 100)
        self.assertEqual(reading.renewable_pct, 40.0)

    def test_renewable_share_with_no_generation(self):
        self.assertEqual(PowerReading(station=self.mai, fuel_level_pct=50).renewable_pct, 0.0)
