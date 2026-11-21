"""Incident emails, maintenance completion and equipment service state."""
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from core.testing import PolarFixtures

from .models import Equipment, Incident, MaintenanceTask


class IncidentEmailTests(PolarFixtures, TestCase):
    def raise_incident(self, station, severity):
        return Incident.objects.create(station=station, title="Fire in galley", description="Smoke",
                                       severity=severity, category=Incident.Category.SAFETY)

    def test_serious_incident_emails_hq_and_own_station_leader(self):
        self.raise_incident(self.mai, Incident.Severity.CRITICAL)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "[PolarOps][CRITICAL] Maitri: Fire in galley")
        self.assertEqual(sorted(message.to), ["hq@example.org", "leader@maitri.example.org"])
        self.assertNotIn("leader@bharati.example.org", message.to)   # other station's leader
        self.assertNotIn("sci@maitri.example.org", message.to)       # not a leader

    def test_minor_incident_sends_no_email(self):
        self.raise_incident(self.mai, Incident.Severity.MEDIUM)
        self.assertEqual(mail.outbox, [])

    def test_updating_an_incident_sends_no_new_email(self):
        incident = self.raise_incident(self.mai, Incident.Severity.HIGH)
        mail.outbox.clear()
        incident.status = Incident.Status.ACKNOWLEDGED
        incident.save()
        self.assertEqual(mail.outbox, [])

    def test_mail_outage_does_not_block_incident_logging(self):
        with mock.patch("operations.signals.send_mail", side_effect=OSError("link down")), \
                self.assertLogs("operations.signals", level="ERROR"):
            incident = self.raise_incident(self.mai, Incident.Severity.HIGH)
        self.assertTrue(Incident.objects.filter(pk=incident.pk).exists())

    def test_resolving_sets_and_reopening_clears_resolved_at(self):
        incident = self.bha_incident
        incident.status = Incident.Status.RESOLVED
        incident.save()
        self.assertIsNotNone(incident.resolved_at)
        incident.status = Incident.Status.OPEN
        incident.save()
        self.assertIsNone(incident.resolved_at)


class MaintenanceTests(PolarFixtures, TestCase):
    def test_completing_a_task_services_the_equipment(self):
        task = MaintenanceTask.objects.create(equipment=self.mai_generator, title="Oil change")
        self.assertIsNone(task.completed_at)
        task.status = MaintenanceTask.Status.DONE
        task.save()
        self.mai_generator.refresh_from_db()
        self.assertIsNotNone(task.completed_at)
        self.assertEqual(self.mai_generator.last_serviced_on, timezone.localdate())

    def test_reopening_clears_completion(self):
        task = MaintenanceTask.objects.create(equipment=self.mai_generator, title="Oil change",
                                              status=MaintenanceTask.Status.DONE)
        task.status = MaintenanceTask.Status.IN_PROGRESS
        task.save()
        self.assertIsNone(task.completed_at)

    def test_completing_through_the_web_form(self):
        task = MaintenanceTask.objects.create(equipment=self.mai_generator, title="Filter swap")
        self.login(self.mai_leader)
        self.client.post(f"/operations/maintenance/{task.pk}/edit/", {
            "equipment": self.mai_generator.pk, "title": "Filter swap", "priority": "MEDIUM", "status": "DONE",
        })
        task.refresh_from_db()
        self.assertEqual(task.status, MaintenanceTask.Status.DONE)
        self.mai_generator.refresh_from_db()
        self.assertIsNotNone(self.mai_generator.last_serviced_on)


class EquipmentServiceStateTests(PolarFixtures, TestCase):
    def state(self, days_ago, interval=90):
        eq = Equipment(station=self.mai, name="x", service_interval_days=interval,
                       last_serviced_on=timezone.localdate() - timedelta(days=days_ago) if days_ago is not None else None)
        return eq.service_state

    def test_states(self):
        self.assertEqual(self.state(None), "UNKNOWN")
        self.assertEqual(self.state(10), "OK")
        self.assertEqual(self.state(80), "DUE_SOON")
        self.assertEqual(self.state(100), "OVERDUE")

    def test_next_service_due(self):
        eq = Equipment(station=self.mai, name="x", service_interval_days=30,
                       last_serviced_on=timezone.localdate())
        self.assertEqual(eq.next_service_due, timezone.localdate() + timedelta(days=30))
