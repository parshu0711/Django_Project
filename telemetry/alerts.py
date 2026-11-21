"""Rules that turn incoming sensor readings into incidents automatically."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from operations.models import Incident


def _cfg(key, default):
    return getattr(settings, "POLAROPS_ALERTS", {}).get(key, default)


def raise_alert(station, title, category, severity, description):
    """Create an auto incident unless the same one is already open in the dedupe window."""
    window = timezone.now() - timedelta(hours=_cfg("DEDUPE_HOURS", 6))
    duplicate = (
        Incident.objects.filter(station=station, title=title, auto_generated=True, reported_at__gte=window)
        .exclude(status=Incident.Status.RESOLVED)
        .exists()
    )
    if duplicate:
        return None
    return Incident.objects.create(
        station=station,
        title=title,
        category=category,
        severity=severity,
        description=description,
        auto_generated=True,
    )


def _when(reading):
    return timezone.localtime(reading.recorded_at).strftime("%d %b %H:%M")


def check_weather(reading):
    created = []
    wind_limit = _cfg("WIND_KMH", 100)
    if reading.wind_speed_kmh >= wind_limit:
        created.append(raise_alert(
            reading.station,
            "Blizzard / high-wind warning",
            Incident.Category.WEATHER,
            Incident.Severity.CRITICAL if reading.wind_speed_kmh >= wind_limit * 1.5 else Incident.Severity.HIGH,
            f"Wind speed of {reading.wind_speed_kmh:.0f} km/h recorded at {_when(reading)} "
            f"(limit {wind_limit:.0f} km/h). Suspend outdoor movement and field trips, secure loose equipment.",
        ))
    if reading.temperature_c <= _cfg("TEMP_C", -45):
        created.append(raise_alert(
            reading.station,
            "Extreme cold warning",
            Incident.Category.WEATHER,
            Incident.Severity.HIGH,
            f"Air temperature {reading.temperature_c:.1f} °C at {_when(reading)}. "
            "Limit outdoor exposure and check heating and fuel lines.",
        ))
    if reading.visibility_km is not None and reading.visibility_km < _cfg("VISIBILITY_KM", 0.2):
        created.append(raise_alert(
            reading.station,
            "Whiteout conditions",
            Incident.Category.WEATHER,
            Incident.Severity.HIGH,
            f"Visibility dropped to {reading.visibility_km * 1000:.0f} m at {_when(reading)}. "
            "No vehicle or helicopter movement.",
        ))
    return [c for c in created if c]


def check_power(reading):
    created = []
    fuel_limit = _cfg("FUEL_PCT", 20)
    if reading.fuel_level_pct <= fuel_limit:
        created.append(raise_alert(
            reading.station,
            "Low fuel reserve",
            Incident.Category.EQUIPMENT,
            Incident.Severity.CRITICAL if reading.fuel_level_pct <= fuel_limit / 2 else Incident.Severity.HIGH,
            f"Main fuel tank at {reading.fuel_level_pct:.0f}% ({_when(reading)}). "
            "Review generator schedule and request a resupply.",
        ))
    if reading.battery_pct is not None and reading.battery_pct <= _cfg("BATTERY_PCT", 15):
        created.append(raise_alert(
            reading.station,
            "Battery bank critically low",
            Incident.Category.EQUIPMENT,
            Incident.Severity.HIGH,
            f"Battery charge {reading.battery_pct:.0f}% at {_when(reading)}. Check inverter and generator sync.",
        ))
    return [c for c in created if c]
