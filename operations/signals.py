"""
Email HQ and the station leader when an incident is raised as HIGH or CRITICAL, or is
escalated to HIGH / CRITICAL later.

The email goes out after the database transaction commits (so a rolled-back incident
never sends one), and EMAIL_TIMEOUT stops a dead satellite mail link from hanging the request.
"""
import logging

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Incident

log = logging.getLogger(__name__)

SERIOUS = (Incident.Severity.HIGH, Incident.Severity.CRITICAL)
SEVERITY_RANK = {value: rank for rank, (value, _) in enumerate(Incident.Severity.choices)}


@receiver(pre_save, sender=Incident)
def remember_previous_severity(sender, instance, **kwargs):
    previous = None
    if instance.pk:
        previous = Incident.objects.filter(pk=instance.pk).values_list("severity", flat=True).first()
    instance._previous_severity = previous


def is_escalation(previous, current):
    """True when an existing incident moved up into HIGH / CRITICAL."""
    return current in SERIOUS and SEVERITY_RANK.get(current, 0) > SEVERITY_RANK.get(previous, -1)


@receiver(post_save, sender=Incident)
def notify_on_serious_incident(sender, instance, created, **kwargs):
    if created:
        if instance.severity not in SERIOUS:
            return
        escalated_from = None
    else:
        previous = getattr(instance, "_previous_severity", None)
        if not is_escalation(previous, instance.severity):
            return
        escalated_from = previous
    pk = instance.pk
    transaction.on_commit(lambda: send_incident_email(pk, escalated_from))


def send_incident_email(pk, escalated_from=None):
    instance = Incident.objects.select_related("station", "reported_by").filter(pk=pk).first()
    if instance is None:
        return
    User = get_user_model()
    recipients = (
        User.objects.filter(is_active=True)
        .filter(
            Q(is_superuser=True)
            | Q(role=User.Role.HQ_ADMIN)
            | Q(role=User.Role.STATION_LEADER, station=instance.station_id)
        )
        .exclude(email="")
        .values_list("email", flat=True)
    )
    recipients = sorted(set(recipients))
    if not recipients:
        return
    when = timezone.localtime(instance.reported_at).strftime("%d %b %Y %H:%M %Z")
    prefix = f"[PolarOps][{instance.severity}]"
    if escalated_from:
        prefix += "[ESCALATED]"
    body = (
        f"Station:   {instance.station.name} ({instance.station.code})\n"
        f"Severity:  {instance.get_severity_display()}"
        + (f" (escalated from {Incident.Severity(escalated_from).label})" if escalated_from else "")
        + "\n"
        f"Category:  {instance.get_category_display()}\n"
        f"Reported:  {when}\n"
        f"Source:    {'Automatic sensor alert' if instance.auto_generated else instance.reported_by or 'Unknown'}\n\n"
        f"{instance.description}\n"
    )
    try:
        send_mail(
            subject=f"{prefix} {instance.station.name}: {instance.title}",
            message=body,
            from_email=None,
            recipient_list=recipients,
        )
        log.info("Incident alert email sent for %s to %d recipient(s)", instance, len(recipients))
    except Exception:  # never block incident logging because mail is down (common on sat links)
        log.exception("Could not send incident alert email")
