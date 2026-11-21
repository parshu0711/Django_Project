"""Email HQ and the station leader whenever a HIGH or CRITICAL incident is raised."""
import logging

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Incident

log = logging.getLogger(__name__)


@receiver(post_save, sender=Incident)
def notify_on_serious_incident(sender, instance, created, **kwargs):
    if not created or instance.severity not in (Incident.Severity.HIGH, Incident.Severity.CRITICAL):
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
    body = (
        f"Station:   {instance.station.name} ({instance.station.code})\n"
        f"Severity:  {instance.get_severity_display()}\n"
        f"Category:  {instance.get_category_display()}\n"
        f"Reported:  {when}\n"
        f"Source:    {'Automatic sensor alert' if instance.auto_generated else instance.reported_by or 'Unknown'}\n\n"
        f"{instance.description}\n"
    )
    try:
        send_mail(
            subject=f"[PolarOps][{instance.severity}] {instance.station.name}: {instance.title}",
            message=body,
            from_email=None,
            recipient_list=recipients,
        )
    except Exception:  # never block incident logging because mail is down (common on sat links)
        log.exception("Could not send incident alert email")
