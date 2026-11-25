"""Role-based access: HQ sees every station, station staff only their own (core/mixins.py)."""
from django.test import TestCase
from django.urls import reverse

from core.testing import PolarFixtures
from operations.models import Incident
from research.models import FieldLog


class StationScopingTests(PolarFixtures, TestCase):
    def test_lists_are_filtered_to_own_station(self):
        self.login(self.mai_leader)
        items = self.client.get(reverse("inventory:item_list")).context["object_list"]
        self.assertEqual(list(items), [self.mai_diesel])

    def test_station_filter_is_ignored_for_station_staff(self):
        self.login(self.mai_leader)
        response = self.client.get(reverse("inventory:item_list"), {"station": self.bha.pk})
        self.assertEqual(list(response.context["object_list"]), [self.mai_diesel])
        self.assertIsNone(response.context["stations"])   # no station dropdown for station staff

    def test_hq_can_filter_by_station(self):
        self.login(self.hq)
        response = self.client.get(reverse("inventory:item_list"), {"station": self.bha.pk})
        self.assertEqual(list(response.context["object_list"]), [self.bha_rice])

    def test_nested_station_lookups_are_scoped(self):
        FieldLog.objects.create(project=self.mai_project, activity="Drilled core")
        FieldLog.objects.create(project=self.bha_project, activity="Camera check")
        self.login(self.bha_engineer)
        logs = self.client.get(reverse("research:log_list")).context["object_list"]
        self.assertEqual([log.activity for log in logs], ["Camera check"])

    def test_other_station_records_are_404(self):
        self.login(self.mai_leader)
        for name, obj in (("inventory:item_detail", self.bha_rice), ("inventory:item_edit", self.bha_rice),
                          ("operations:incident_detail", self.bha_incident),
                          ("personnel:member_detail", self.bha_member), ("stations:station_detail", self.bha)):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name, args=[obj.pk])).status_code, 404)

    def test_user_without_station_sees_nothing(self):
        self.login(self.unassigned)
        self.assertEqual(len(self.client.get(reverse("inventory:item_list")).context["object_list"]), 0)

    def test_hq_only_forms_reject_station_staff_posts(self):
        self.login(self.mai_leader)
        response = self.client.post(reverse("personnel:expedition_create"),
                                    {"code": "ISEA-99", "name": "Rogue", "start_date": "2026-01-01"})
        self.assertEqual(response.status_code, 403)

    def test_form_choices_limited_to_own_station(self):
        self.login(self.mai_leader)
        form = self.client.get(reverse("operations:incident_create")).context["form"]
        self.assertEqual(list(form.fields["station"].queryset), [self.mai])
        self.assertEqual(form.initial["station"], self.mai.pk)
        task_form = self.client.get(reverse("operations:task_create")).context["form"]
        self.assertEqual(list(task_form.fields["equipment"].queryset), [self.mai_generator])

    def test_cannot_post_for_another_station(self):
        self.login(self.mai_leader)
        response = self.client.post(reverse("operations:incident_create"), {
            "station": self.bha.pk, "title": "Spoof", "category": "OTHER", "severity": "LOW",
            "status": "OPEN", "reported_at": "2026-11-21T10:00", "description": "x",
        })
        self.assertEqual(response.status_code, 200)            # form redisplayed with an error
        self.assertIn("station", response.context["form"].errors)
        self.assertFalse(Incident.objects.filter(title="Spoof").exists())

    def test_create_records_the_reporting_user(self):
        self.login(self.mai_leader)
        response = self.client.post(reverse("operations:incident_create"), {
            "station": self.mai.pk, "title": "Frostbite", "category": "MEDICAL", "severity": "MEDIUM",
            "status": "OPEN", "reported_at": "2026-11-21T10:00", "description": "Mild case",
        })
        incident = Incident.objects.get(title="Frostbite")
        self.assertRedirects(response, reverse("operations:incident_detail", args=[incident.pk]))
        self.assertEqual(incident.reported_by, self.mai_leader)

    def test_prefill_from_query_string(self):
        self.login(self.mai_leader)
        form = self.client.get(reverse("inventory:movement_create"), {"item": self.mai_diesel.pk}).context["form"]
        self.assertEqual(str(form.initial["item"]), str(self.mai_diesel.pk))


class MedicalConfidentialityTests(PolarFixtures, TestCase):
    def test_scientist_and_engineer_cannot_open_medical_records(self):
        for user in (self.mai_scientist, self.bha_engineer):
            self.login(user)
            for name in ("personnel:medical_list", "personnel:medical_create"):
                with self.subTest(user=user.username, page=name):
                    self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_leader_medical_officer_and_hq_can(self):
        from django.contrib.auth import get_user_model
        doctor = get_user_model().objects.create_user("mai_doctor", role="MEDICAL", station=self.mai)
        for user in (self.mai_leader, doctor, self.hq):
            self.login(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(reverse("personnel:medical_list")).status_code, 200)

    def test_menu_and_member_page_hide_medical_checks_from_other_roles(self):
        self.login(self.mai_scientist)
        response = self.client.get(self.mai_member.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("personnel:medical_list"))
        self.assertEqual(response.context["related_blocks"], [])
        self.login(self.mai_leader)
        response = self.client.get(self.mai_member.get_absolute_url())
        self.assertContains(response, reverse("personnel:medical_list"))
        self.assertEqual([b["title"] for b in response.context["related_blocks"]], ["Medical checks"])
