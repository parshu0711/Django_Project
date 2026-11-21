"""Landing page, dashboard, top navigation and a smoke test of every page."""
from django.test import TestCase, override_settings
from django.urls import reverse

from core.testing import PolarFixtures
from operations.models import Incident

LIST_AND_CREATE_PAGES = [
    "stations:station_list", "stations:station_create", "stations:sitrep_list", "stations:sitrep_create",
    "personnel:member_list", "personnel:member_create", "personnel:expedition_list", "personnel:expedition_create",
    "personnel:medical_list", "personnel:medical_create",
    "inventory:item_list", "inventory:item_create", "inventory:movement_list", "inventory:movement_create",
    "inventory:shipment_list", "inventory:shipment_create",
    "operations:equipment_list", "operations:equipment_create", "operations:task_list", "operations:task_create",
    "operations:incident_list", "operations:incident_create",
    "telemetry:weather_list", "telemetry:weather_create", "telemetry:power_list", "telemetry:power_create",
    "research:project_list", "research:project_create", "research:log_list", "research:log_create",
]
HQ_ONLY_WRITE = {"stations:station_create", "personnel:expedition_create"}


class LandingPageTests(PolarFixtures, TestCase):
    def test_public_and_lists_stations(self):
        response = self.client.get(reverse("core:landing"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/landing.html")
        for name in ("Maitri", "Bharati", "Dakshin Gangotri"):
            self.assertContains(response, name)
        self.assertContains(response, reverse("accounts:login"))
        self.assertEqual(response.context["active_count"], 2)

    def test_does_not_leak_operational_data(self):
        response = self.client.get(reverse("core:landing"))
        for secret in ("Arctic diesel", "Generator trip", "Ravi Kumar", "Ice core study"):
            self.assertNotContains(response, secret)
        points = response.context["map_points"]
        self.assertEqual(len(points), 3)
        for p in points:
            self.assertNotIn("crew", p)
            self.assertNotIn("incidents", p)
            self.assertNotIn("url", p)

    def test_signed_in_user_gets_dashboard_button(self):
        self.login(self.mai_leader)
        response = self.client.get(reverse("core:landing"))
        self.assertContains(response, "Open dashboard")
        self.assertContains(response, reverse("core:dashboard"))


class GoogleMapsKeyTests(PolarFixtures, TestCase):
    @override_settings(GOOGLE_MAPS_API_KEY="TestMapsKey123")
    def test_key_is_passed_to_map_pages(self):
        self.assertContains(self.client.get(reverse("core:landing")), 'window.POLAR_GMAPS_KEY = "TestMapsKey123"')
        self.login(self.hq)
        self.assertContains(self.client.get(reverse("core:dashboard")), 'window.POLAR_GMAPS_KEY = "TestMapsKey123"')

    @override_settings(GOOGLE_MAPS_API_KEY='abc";alert(1);//')
    def test_key_is_escaped_for_javascript(self):
        self.assertNotContains(self.client.get(reverse("core:landing")), 'alert(1);//"')

    @override_settings(GOOGLE_MAPS_API_KEY="")
    def test_no_key_means_openstreetmap_fallback(self):
        response = self.client.get(reverse("core:landing"))
        self.assertNotContains(response, "POLAR_GMAPS_KEY")
        self.assertContains(response, "leaflet.js")


class DashboardTests(PolarFixtures, TestCase):
    def test_requires_login(self):
        url = reverse("core:dashboard")
        self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={url}")

    def test_hq_sees_every_station(self):
        self.login(self.hq)
        response = self.client.get(reverse("core:dashboard"))
        codes = {c["station"].code for c in response.context["cards"]}
        self.assertEqual(codes, {"MAI", "BHA", "DKG"})
        self.assertEqual(response.context["kpis"]["low_stock"], 1)
        self.assertEqual(response.context["kpis"]["open_incidents"], 1)

    def test_station_user_sees_only_own_station(self):
        self.login(self.mai_leader)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual([c["station"].code for c in response.context["cards"]], ["MAI"])
        self.assertEqual(response.context["kpis"]["low_stock"], 0)      # the low item is at Bharati
        self.assertEqual(response.context["kpis"]["open_incidents"], 0)
        self.assertNotContains(response, "Generator trip")

    def test_greets_user_by_name(self):
        self.login(self.hq)
        response = self.client.get(reverse("core:dashboard"))
        self.assertContains(response, "Hq</h1>")
        self.assertIn(response.context["greeting"], ("Good morning", "Good afternoon", "Good evening"))


class TopNavigationTests(PolarFixtures, TestCase):
    def test_top_navbar_replaces_sidebar(self):
        self.login(self.hq)
        html = self.client.get(reverse("core:dashboard")).content.decode()
        self.assertIn('class="navbar navbar-expand-lg app-nav', html)
        self.assertNotIn("sidebar", html)
        for menu in ("Stations", "Telemetry", "People", "Logistics", "Operations", "Science"):
            self.assertIn(f"<span>{menu}</span>", html)

    def test_active_menu_is_highlighted(self):
        self.login(self.hq)
        html = self.client.get(reverse("inventory:item_list")).content.decode()
        self.assertRegex(html, r'dropdown-toggle active"[^>]*><i class="bi bi-box-seam"></i><span>Logistics')
        self.assertNotRegex(html, r'dropdown-toggle active"[^>]*><i class="bi bi-people"></i><span>People')

    def test_incident_badge_is_scoped_to_station(self):
        self.login(self.bha_leader)
        self.assertEqual(self.client.get(reverse("core:dashboard")).context["nav_open_incidents"], 1)
        self.login(self.mai_leader)
        self.assertEqual(self.client.get(reverse("core:dashboard")).context["nav_open_incidents"], 0)

    def test_resolved_incidents_leave_the_badge(self):
        Incident.objects.filter(pk=self.bha_incident.pk).update(status=Incident.Status.RESOLVED)
        self.login(self.hq)
        self.assertEqual(self.client.get(reverse("core:dashboard")).context["nav_open_incidents"], 0)

    def test_admin_link_only_for_staff(self):
        self.login(self.mai_leader)
        self.assertNotContains(self.client.get(reverse("core:dashboard")), reverse("admin:index"))
        self.hq.is_staff = True
        self.hq.save()
        self.login(self.hq)
        self.assertContains(self.client.get(reverse("core:dashboard")), reverse("admin:index"))


class PageSmokeTests(PolarFixtures, TestCase):
    def test_every_list_and_form_page_renders_for_hq(self):
        self.login(self.hq)
        for name in LIST_AND_CREATE_PAGES:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_station_staff_get_403_only_on_hq_only_forms(self):
        self.login(self.mai_leader)
        for name in LIST_AND_CREATE_PAGES:
            with self.subTest(page=name):
                expected = 403 if name in HQ_ONLY_WRITE else 200
                self.assertEqual(self.client.get(reverse(name)).status_code, expected)

    def test_detail_and_edit_pages_render(self):
        self.login(self.hq)
        objects = {
            "stations:station": self.mai, "personnel:member": self.mai_member,
            "personnel:expedition": self.expedition, "inventory:item": self.mai_diesel,
            "operations:equipment": self.mai_generator, "operations:incident": self.bha_incident,
            "research:project": self.mai_project,
        }
        for base, obj in objects.items():
            for suffix in ("detail", "edit"):
                with self.subTest(page=f"{base}_{suffix}"):
                    self.assertEqual(self.client.get(reverse(f"{base}_{suffix}", args=[obj.pk])).status_code, 200)

    def test_csv_export(self):
        self.login(self.hq)
        response = self.client.get(reverse("inventory:item_list"), {"export": "csv"})
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment;", response["Content-Disposition"])
        lines = response.content.decode().strip().splitlines()
        self.assertTrue(lines[0].startswith("Item,Station,Category"))
        self.assertEqual(len(lines), 3)   # header + two items

    def test_low_stock_filter(self):
        self.login(self.hq)
        response = self.client.get(reverse("inventory:item_list"), {"low": "1"})
        self.assertEqual(list(response.context["object_list"]), [self.bha_rice])
        self.assertEqual(response.context["title"], "Low-stock items")
