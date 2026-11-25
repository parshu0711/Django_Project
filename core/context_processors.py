from django.conf import settings


def maps(request):
    return {"GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY}


def demo(request):
    """Demo account switcher. demo_accounts is passed as a callable so it only queries when a page uses it."""
    if not settings.DEMO_MODE:
        return {}
    from accounts.demo import demo_accounts

    return {"DEMO_MODE": True, "demo_accounts": demo_accounts}


def navigation(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    from operations.models import Incident

    qs = Incident.objects.exclude(status=Incident.Status.RESOLVED)
    if not user.is_hq:
        qs = qs.filter(station_id=user.station_id)
    return {"nav_open_incidents": qs.count()}


def platform(request):
    """Alert thresholds, so chart threshold lines match the alert rules."""
    alerts = settings.POLAROPS_ALERTS
    return {
        "ALERT_THRESHOLDS": {
            "wind_kmh": alerts["WIND_KMH"],
            "temp_c": alerts["TEMP_C"],
            "visibility_km": alerts["VISIBILITY_KM"],
            "fuel_pct": alerts["FUEL_PCT"],
            "battery_pct": alerts["BATTERY_PCT"],
        },
    }
