from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.shortcuts import render
from django.utils import timezone

from inventory.models import Item, Shipment
from operations.models import Equipment, Incident, MaintenanceTask
from personnel.models import Member
from stations.models import Station


def _ts(reading):
    return int(reading.recorded_at.timestamp() * 1000)


def landing(request):
    """Public home page. Shows only public facts about the stations, never live operational data."""
    stations = list(Station.objects.all())
    context = {
        "stations": stations,
        "active_count": sum(1 for s in stations if s.status == Station.Status.ACTIVE),
        "map_points": [
            {
                "name": s.name,
                "code": s.code,
                "lat": float(s.latitude),
                "lng": float(s.longitude),
                "status": s.status,
                "status_label": s.get_status_display(),
                "established": s.established,
            }
            for s in stations
        ],
    }
    return render(request, "core/landing.html", context)


def _greeting():
    hour = timezone.localtime().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


@login_required
def dashboard(request):
    user = request.user
    if user.is_sensor:
        raise PermissionDenied("Sensor accounts can only upload telemetry through the API.")
    stations = Station.objects.all() if user.is_hq else Station.objects.filter(pk=user.station_id)
    ids = list(stations.values_list("pk", flat=True))
    open_incidents = Incident.objects.filter(station__in=ids).exclude(status=Incident.Status.RESOLVED)
    present = [Member.Status.ON_STATION, Member.Status.ON_FIELD]

    cards = []
    for st in stations:
        cards.append({
            "station": st,
            "weather": st.latest_weather,
            "power": st.latest_power,
            "sitrep": st.sitreps.first(),
            "crew": st.members.filter(status__in=present).count(),
            "open_incidents": st.incidents.exclude(status=Incident.Status.RESOLVED).count(),
        })

    kpis = {
        "stations_active": stations.filter(status=Station.Status.ACTIVE).count(),
        "stations_total": len(ids),
        "crew": Member.objects.filter(station__in=ids, status__in=present).count(),
        "in_transit": Member.objects.filter(station__in=ids, status=Member.Status.IN_TRANSIT).count(),
        "open_incidents": open_incidents.count(),
        "serious_incidents": open_incidents.filter(
            severity__in=[Incident.Severity.HIGH, Incident.Severity.CRITICAL]
        ).count(),
        "low_stock": Item.objects.filter(station__in=ids, quantity__lte=F("min_threshold")).count(),
        "faulty": Equipment.objects.filter(station__in=ids, status=Equipment.Status.FAULTY).count(),
        "open_tasks": MaintenanceTask.objects.filter(equipment__station__in=ids).exclude(
            status=MaintenanceTask.Status.DONE
        ).count(),
        "shipments": Shipment.objects.filter(station__in=ids).exclude(status=Shipment.Status.DELIVERED).count(),
    }

    since = timezone.now() - timedelta(hours=72)
    temp_series, wind_series, fuel_series = [], [], []
    for st in stations.filter(status=Station.Status.ACTIVE):
        weather = list(st.weather_readings.filter(recorded_at__gte=since).order_by("recorded_at"))
        power = list(st.power_readings.filter(recorded_at__gte=since).order_by("recorded_at"))
        temp_series.append({"label": st.name, "points": [[_ts(r), r.temperature_c] for r in weather]})
        wind_series.append({"label": st.name, "points": [[_ts(r), r.wind_speed_kmh] for r in weather]})
        fuel_series.append({"label": st.name, "points": [[_ts(r), r.fuel_level_pct] for r in power]})

    map_points = [
        {
            "name": c["station"].name,
            "code": c["station"].code,
            "lat": float(c["station"].latitude),
            "lng": float(c["station"].longitude),
            "status": c["station"].status,
            "status_label": c["station"].get_status_display(),
            "url": c["station"].get_absolute_url(),
            "crew": c["crew"],
            "temp": c["weather"].temperature_c if c["weather"] else None,
            "incidents": c["open_incidents"],
        }
        for c in cards
    ]

    context = {
        "cards": cards,
        "kpis": kpis,
        "recent_incidents": open_incidents.select_related("station")[:8],
        "low_stock_items": Item.objects.filter(station__in=ids, quantity__lte=F("min_threshold")).select_related(
            "station"
        )[:8],
        "shipments": Shipment.objects.filter(station__in=ids)
        .exclude(status=Shipment.Status.DELIVERED)
        .select_related("station")
        .order_by("eta")[:5],
        "chart_data": {"temperature": temp_series, "wind": wind_series, "fuel": fuel_series},
        "map_points": map_points,
        "greeting": _greeting(),
    }
    return render(request, "core/dashboard.html", context)
