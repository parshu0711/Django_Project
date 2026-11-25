from datetime import timedelta

from django.db.models import Count, F
from django.utils import timezone
from django.views.generic import DetailView

from core.mixins import CrudCreateView, CrudDetailView, CrudListView, CrudUpdateView, StationScopedMixin
from inventory.models import Shipment
from operations.models import Incident
from personnel.models import Member
from research.models import Project

from .models import SitRep, Station

STATION_FIELDS = [
    "name", "code", "status", "region", "latitude", "longitude", "established",
    "capacity_winter", "capacity_summer", "communications", "description",
]


class StationBase:
    model = Station
    station_field = "pk"
    url_base = "stations:station"
    hq_only_write = True


class StationList(StationBase, CrudListView):
    title = "Research stations"
    subtitle = "Indian permanent and seasonal bases in Antarctica"
    show_station_filter = False
    columns = (
        ("Station", "name"), ("Code", "code"), ("Region", "region"), ("Status", "status"),
        ("Established", "established"), ("Winter capacity", "capacity_winter"), ("Summer capacity", "capacity_summer"),
    )
    badge_fields = ("status",)
    search_fields = ("name", "code", "region")
    filter_fields = ("status",)


class StationCreate(StationBase, CrudCreateView):
    fields = STATION_FIELDS


class StationUpdate(StationBase, CrudUpdateView):
    fields = STATION_FIELDS


def _ts(reading):
    return int(reading.recorded_at.timestamp() * 1000)


class StationDetail(StationScopedMixin, DetailView):
    model = Station
    station_field = "pk"
    template_name = "stations/station_detail.html"

    def get_queryset(self):
        return self.scope(super().get_queryset())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        st = self.object
        since = timezone.now() - timedelta(days=7)
        weather = list(st.weather_readings.filter(recorded_at__gte=since).order_by("recorded_at"))
        power = list(st.power_readings.filter(recorded_at__gte=since).order_by("recorded_at"))
        ctx["chart_data"] = {
            "temperature": [{"label": "Temperature", "points": [[_ts(r), r.temperature_c] for r in weather]}],
            "wind": [{"label": "Wind speed", "points": [[_ts(r), r.wind_speed_kmh] for r in weather]}],
            "power": [
                {"label": "Diesel generator", "points": [[_ts(r), r.generator_kw] for r in power], "color": "#0d1117"},
                {"label": "Solar", "points": [[_ts(r), r.solar_kw] for r in power], "color": "#d99a00"},
                {"label": "Wind turbine", "points": [[_ts(r), r.wind_kw] for r in power], "color": "#2a5bff"},
            ],
            "fuel": [{"label": "Fuel tank", "points": [[_ts(r), r.fuel_level_pct] for r in power], "color": "#ff5a1f"}],
        }
        ctx["weather"] = st.latest_weather
        ctx["power"] = st.latest_power
        ctx["crew"] = st.members.filter(
            status__in=[Member.Status.ON_STATION, Member.Status.ON_FIELD]
        ).select_related("expedition")
        ctx["low_stock"] = st.items.filter(quantity__lte=F("min_threshold"))
        ctx["equipment"] = st.equipment.all()
        ctx["equipment_summary"] = dict(st.equipment.values_list("status").annotate(n=Count("id")))
        ctx["incidents"] = st.incidents.exclude(status=Incident.Status.RESOLVED)[:10]
        ctx["sitreps"] = st.sitreps.select_related("author")[:5]
        ctx["projects"] = st.projects.filter(status=Project.Status.ACTIVE)
        ctx["shipments"] = st.shipments.exclude(status=Shipment.Status.DELIVERED).order_by("eta")
        return ctx


# ------------------------------------------------------------ situation reports
SITREP_FIELDS = [
    "station", "report_date", "overall_status", "personnel_on_station", "weather_summary",
    "activities", "issues", "requests_to_hq",
]


class SitRepBase:
    model = SitRep
    url_base = "stations:sitrep"


class SitRepList(SitRepBase, CrudListView):
    title = "Situation reports"
    subtitle = "Daily SITREPs sent from stations to NCPOR HQ"
    related = ("station", "author")
    columns = (
        ("Report", "__str__"), ("Date", "report_date"), ("Station", "station"), ("Status", "overall_status"),
        ("Crew", "personnel_on_station"), ("Weather", "weather_summary"), ("Author", "author"),
    )
    badge_fields = ("overall_status",)
    search_fields = ("activities", "issues", "requests_to_hq")
    filter_fields = ("overall_status",)


class SitRepCreate(SitRepBase, CrudCreateView):
    fields = SITREP_FIELDS
    user_field = "author"


class SitRepUpdate(SitRepBase, CrudUpdateView):
    fields = SITREP_FIELDS


class SitRepDetail(SitRepBase, CrudDetailView):
    badge_fields = ("overall_status",)
