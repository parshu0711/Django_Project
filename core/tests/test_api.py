"""REST API: token auth, bulk sensor uploads, station scoping and filters."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.testing import TEST_PASSWORD, PolarFixtures
from operations.models import Incident
from telemetry.models import PowerReading, WeatherReading


def calm(code="MAI", **extra):
    return {"station": code, "temperature_c": -12.0, "wind_speed_kmh": 20, "pressure_hpa": 985, **extra}


class ApiAuthTests(PolarFixtures, TestCase):
    def test_anonymous_requests_are_rejected(self):
        for url in ("/api/live/", "/api/weather/", "/api/stations/"):
            with self.subTest(url=url):
                self.assertIn(self.client.get(url).status_code, (401, 403))

    def test_obtain_token(self):
        response = self.client.post(reverse("api-token"), {"username": "mai_sensor", "password": TEST_PASSWORD})
        self.assertEqual(response.json()["token"], self.mai_token.key)

    def test_session_auth_works_for_the_browser(self):
        self.login(self.hq)
        self.assertEqual(self.client.get("/api/live/").status_code, 200)


class SensorUploadTests(PolarFixtures, TestCase):
    def setUp(self):
        self.auth = {"HTTP_AUTHORIZATION": f"Token {self.mai_token.key}"}

    def post(self, url, payload, **headers):
        return self.client.post(url, payload, content_type="application/json", **{**self.auth, **headers})

    def test_single_reading(self):
        response = self.post("/api/weather/", calm())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["station"], "MAI")
        self.assertEqual(WeatherReading.objects.count(), 1)

    def test_bulk_store_and_forward_upload(self):
        now = timezone.now()
        batch = [calm(recorded_at=(now - timedelta(hours=h)).isoformat()) for h in range(5)]
        response = self.post("/api/weather/", batch)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.json()), 5)
        self.assertEqual(WeatherReading.objects.filter(station=self.mai).count(), 5)

    def test_sensor_cannot_write_for_another_station(self):
        response = self.post("/api/weather/", calm("BHA"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("own station", response.content.decode())
        self.assertFalse(WeatherReading.objects.exists())

    def test_one_bad_reading_rejects_the_whole_batch(self):
        response = self.post("/api/weather/", [calm(), calm("BHA")])
        self.assertEqual(response.status_code, 400)
        self.assertFalse(WeatherReading.objects.exists())

    def test_unknown_station_code(self):
        self.assertEqual(self.post("/api/weather/", calm("XYZ")).status_code, 400)

    def test_hq_can_write_for_any_station(self):
        self.login(self.hq)
        response = self.client.post("/api/power/", {"station": "BHA", "fuel_level_pct": 70, "solar_kw": 5,
                                                    "generator_kw": 15}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["renewable_pct"], 25.0)

    def test_storm_reading_raises_alert_through_api(self):
        self.post("/api/weather/", calm(wind_speed_kmh=130))
        self.assertTrue(Incident.objects.filter(station=self.mai, auto_generated=True,
                                                title__startswith="Blizzard").exists())


class ApiReadTests(PolarFixtures, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        now = timezone.now()
        WeatherReading.objects.create(station=cls.mai, recorded_at=now - timedelta(days=3),
                                      temperature_c=-20, wind_speed_kmh=10, pressure_hpa=980)
        WeatherReading.objects.create(station=cls.mai, recorded_at=now, temperature_c=-10, wind_speed_kmh=10,
                                      pressure_hpa=980)
        WeatherReading.objects.create(station=cls.bha, recorded_at=now, temperature_c=-5, wind_speed_kmh=10,
                                      pressure_hpa=980)
        PowerReading.objects.create(station=cls.mai, fuel_level_pct=80, battery_pct=90)

    def test_station_user_only_reads_own_station(self):
        self.login(self.bha_engineer)
        data = self.client.get("/api/weather/").json()
        self.assertEqual(data["count"], 1)
        self.assertEqual({r["station"] for r in data["results"]}, {"BHA"})
        self.assertEqual([s["code"] for s in self.client.get("/api/stations/").json()["results"]], ["BHA"])

    def test_station_and_since_filters(self):
        self.login(self.hq)
        since = (timezone.now() - timedelta(days=1)).isoformat()
        data = self.client.get("/api/weather/", {"station": "mai", "since": since}).json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["temperature_c"], -10)

    def test_open_incidents_filter_and_patch(self):
        self.login(self.hq)
        self.assertEqual(self.client.get("/api/incidents/", {"open": 1}).json()["count"], 1)
        url = f"/api/incidents/{self.bha_incident.pk}/"
        response = self.client.patch(url, {"status": "RESOLVED"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["resolved_at"])
        self.assertEqual(self.client.get("/api/incidents/", {"open": 1}).json()["count"], 0)

    def test_incidents_cannot_be_deleted(self):
        self.login(self.hq)
        self.assertEqual(self.client.delete(f"/api/incidents/{self.bha_incident.pk}/").status_code, 405)

    def test_low_stock_filter(self):
        self.login(self.hq)
        data = self.client.get("/api/inventory/", {"low": 1}).json()
        self.assertEqual([i["name"] for i in data["results"]], ["Rice"])
        self.assertTrue(data["results"][0]["is_low"])

    def test_live_status_shape(self):
        self.login(self.mai_leader)
        data = self.client.get("/api/live/").json()
        self.assertEqual(len(data["stations"]), 1)
        mai = data["stations"][0]
        self.assertEqual(mai["code"], "MAI")
        self.assertEqual(mai["weather"]["temperature_c"], -10)
        self.assertEqual(mai["power"]["fuel_level_pct"], 80)
        self.assertEqual(mai["open_incidents"], 0)
