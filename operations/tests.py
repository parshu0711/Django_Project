"""Incident emails, maintenance completion and equipment service state."""
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.core import mail
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.testing import PolarFixtures

from .models import Equipment, Incident, MaintenanceTask


class IncidentEmailTests(PolarFixtures, TestCase):
    def raise_incident(self, station, severity):
        with self.captureOnCommitCallbacks(execute=True):
            return Incident.objects.create(station=station, title="Fire in galley", description="Smoke",
                                           severity=severity, category=Incident.Category.SAFETY)

    def save(self, incident):
        with self.captureOnCommitCallbacks(execute=True):
            incident.save()

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
        self.save(incident)
        self.assertEqual(mail.outbox, [])

    def test_escalation_to_critical_sends_email(self):
        incident = self.raise_incident(self.mai, Incident.Severity.MEDIUM)
        self.assertEqual(mail.outbox, [])
        incident.severity = Incident.Severity.CRITICAL
        self.save(incident)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("[ESCALATED]", mail.outbox[0].subject)
        self.assertIn("escalated from Medium", mail.outbox[0].body)

    def test_high_to_critical_is_an_escalation_but_critical_to_high_is_not(self):
        incident = self.raise_incident(self.mai, Incident.Severity.HIGH)
        incident.severity = Incident.Severity.CRITICAL
        self.save(incident)
        self.assertEqual(len(mail.outbox), 2)
        incident.severity = Incident.Severity.HIGH
        self.save(incident)
        self.assertEqual(len(mail.outbox), 2)

    def test_no_email_when_the_transaction_rolls_back(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            try:
                with transaction.atomic():
                    Incident.objects.create(station=self.mai, title="Fire", description="x",
                                            severity=Incident.Severity.CRITICAL)
                    raise RuntimeError("form failed later")
            except RuntimeError:
                pass
        self.assertEqual(callbacks, [])
        self.assertEqual(mail.outbox, [])

    def test_email_timeout_is_configured(self):
        self.assertGreater(settings.EMAIL_TIMEOUT, 0)

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

    def test_completion_is_atomic_with_the_task_save(self):
        task = MaintenanceTask.objects.create(equipment=self.mai_generator, title="Oil change")
        task.status = MaintenanceTask.Status.DONE
        with mock.patch("django.db.models.Model.save", side_effect=RuntimeError("db error")):
            with self.assertRaises(RuntimeError):
                task.save()
        self.mai_generator.refresh_from_db()
        self.assertIsNone(self.mai_generator.last_serviced_on)

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


class IncidentAcknowledgementTests(PolarFixtures, TestCase):
    def form_data(self, **extra):
        return {"station": self.bha.pk, "title": "Generator trip", "category": "EQUIPMENT", "severity": "LOW",
                "status": "OPEN", "reported_at": "2026-11-20T10:00", "description": "Tripped", **extra}

    def edit_url(self):
        return reverse("operations:incident_edit", args=[self.bha_incident.pk])

    def test_station_staff_cannot_acknowledge(self):
        self.login(self.bha_leader)
        response = self.client.post(self.edit_url(), self.form_data(status="ACKNOWLEDGED"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only HQ can acknowledge")
        self.bha_incident.refresh_from_db()
        self.assertEqual(self.bha_incident.status, Incident.Status.OPEN)

    def test_station_staff_can_keep_an_acknowledged_incident_and_resolve_it(self):
        Incident.objects.filter(pk=self.bha_incident.pk).update(status=Incident.Status.ACKNOWLEDGED)
        self.login(self.bha_leader)
        response = self.client.post(self.edit_url(), self.form_data(status="ACKNOWLEDGED", action_taken="Restarted"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.post(self.edit_url(), self.form_data(status="RESOLVED")).status_code, 302)

    def test_hq_can_acknowledge(self):
        self.login(self.hq)
        self.assertEqual(self.client.post(self.edit_url(), self.form_data(status="ACKNOWLEDGED")).status_code, 302)
        self.bha_incident.refresh_from_db()
        self.assertEqual(self.bha_incident.status, Incident.Status.ACKNOWLEDGED)

    def test_station_prefill_still_works_on_the_incident_form(self):
        self.login(self.hq)
        response = self.client.get(reverse("operations:incident_create"), {"station": self.bha.pk})
        self.assertEqual(response.context["form"].initial["station"], str(self.bha.pk))
