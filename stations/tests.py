from django.test import TestCase
from django.urls import reverse

from core.testing import PolarFixtures
from personnel.models import MedicalCheck
from research.models import FieldLog

from .models import SitRep


class AuthorFieldTests(PolarFixtures, TestCase):
    """Forms that record who filed the record: SITREP author, medical examiner, field-log author."""

    def test_sitrep_records_author(self):
        self.login(self.mai_leader)
        response = self.client.post(reverse("stations:sitrep_create"), {
            "station": self.mai.pk, "report_date": "2026-11-20", "overall_status": "AMBER",
            "personnel_on_station": 24, "activities": "Fuel transfer", "issues": "", "requests_to_hq": "",
        })
        sitrep = SitRep.objects.get()
        self.assertRedirects(response, sitrep.get_absolute_url())
        self.assertEqual(sitrep.author, self.mai_leader)
        self.assertEqual(str(sitrep), "MAI SITREP 20 Nov 2026")

    def test_medical_check_records_examiner(self):
        self.login(self.mai_leader)
        self.client.post(reverse("personnel:medical_create"), {
            "member": self.mai_member.pk, "checked_on": "2026-11-20", "bp_systolic": 120, "bp_diastolic": 80,
            "fit_for_duty": "on",
        })
        check = MedicalCheck.objects.get()
        self.assertEqual(check.examiner, self.mai_leader)
        self.assertEqual(check.blood_pressure, "120/80")

    def test_field_log_records_author(self):
        self.login(self.mai_scientist)
        self.client.post(reverse("research:log_create"), {
            "project": self.mai_project.pk, "log_date": "2026-11-20", "activity": "Snow pit sampling",
        })
        self.assertEqual(FieldLog.objects.get().author, self.mai_scientist)


class StationDetailTests(PolarFixtures, TestCase):
    def test_station_page_renders_for_own_station(self):
        self.login(self.mai_leader)
        response = self.client.get(self.mai.get_absolute_url())
        self.assertContains(response, "Maitri")

    def test_only_hq_can_edit_stations(self):
        self.login(self.mai_leader)
        self.assertEqual(self.client.get(reverse("stations:station_edit", args=[self.mai.pk])).status_code, 403)
        self.login(self.hq)
        self.assertEqual(self.client.get(reverse("stations:station_edit", args=[self.mai.pk])).status_code, 200)
