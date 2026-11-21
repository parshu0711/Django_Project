from django.db.models.signals import post_save
from django.dispatch import receiver

from . import alerts
from .models import PowerReading, WeatherReading


@receiver(post_save, sender=WeatherReading)
def weather_saved(sender, instance, created, **kwargs):
    if created:
        alerts.check_weather(instance)


@receiver(post_save, sender=PowerReading)
def power_saved(sender, instance, created, **kwargs):
    if created:
        alerts.check_power(instance)
