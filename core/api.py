"""
REST API (Django REST Framework).

Sensors and field devices authenticate with a token:
    Authorization: Token <key>

POST /api/weather/ and /api/power/ accept a single reading or a JSON list of
readings, so a station gateway can buffer data while the satellite link is
down and upload it in one batch when the link returns (store-and-forward).
"""
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from inventory.models import Item
from operations.models import Incident
from stations.models import Station
from telemetry.models import PowerReading, WeatherReading


# ---------------------------------------------------------------- helpers
class StationCodeField(serializers.SlugRelatedField):
    def __init__(self, **kwargs):
        kwargs.setdefault("queryset", Station.objects.all())
        super().__init__(slug_field="code", **kwargs)


class OwnStationMixin:
    def validate_station(self, station):
        user = self.context["request"].user
        if not user.is_hq and station.pk != user.station_id:
            raise serializers.ValidationError("You can only submit data for your own station.")
        return station


class ScopedQuerysetMixin:
    station_field = "station"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_hq:
            qs = qs.filter(**{self.station_field: user.station_id}) if user.station_id else qs.none()
        code = self.request.query_params.get("station")
        if code:
            qs = qs.filter(**{f"{self.station_field}__code__iexact": code})
        since = parse_datetime(self.request.query_params.get("since", "") or "")
        if since and hasattr(qs.model, "recorded_at"):
            qs = qs.filter(recorded_at__gte=since)
        return qs


class BulkCreateMixin:
    def create(self, request, *args, **kwargs):
        many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ------------------------------------------------------------ serializers
class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = [
            "id", "name", "code", "status", "region", "latitude", "longitude", "established",
            "capacity_winter", "capacity_summer", "communications",
        ]


class WeatherReadingSerializer(OwnStationMixin, serializers.ModelSerializer):
    station = StationCodeField()

    class Meta:
        model = WeatherReading
        fields = [
            "id", "station", "recorded_at", "temperature_c", "wind_speed_kmh", "wind_direction_deg",
            "pressure_hpa", "humidity_pct", "visibility_km", "source",
        ]


class PowerReadingSerializer(OwnStationMixin, serializers.ModelSerializer):
    station = StationCodeField()
    renewable_pct = serializers.FloatField(read_only=True)

    class Meta:
        model = PowerReading
        fields = [
            "id", "station", "recorded_at", "generator_kw", "solar_kw", "wind_kw", "load_kw",
            "fuel_level_pct", "battery_pct", "renewable_pct",
        ]


class IncidentSerializer(OwnStationMixin, serializers.ModelSerializer):
    station = StationCodeField()
    reported_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id", "station", "title", "category", "severity", "status", "description", "action_taken",
            "reported_by", "reported_at", "resolved_at", "auto_generated",
        ]
        read_only_fields = ["resolved_at", "auto_generated"]


class ItemSerializer(serializers.ModelSerializer):
    station = serializers.SlugRelatedField(slug_field="code", read_only=True)
    is_low = serializers.BooleanField(read_only=True)

    class Meta:
        model = Item
        fields = ["id", "station", "name", "category", "unit", "quantity", "min_threshold", "is_low", "updated_at"]


# --------------------------------------------------------------- viewsets
class StationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer

    def get_queryset(self):
        user = self.request.user
        return self.queryset if user.is_hq else self.queryset.filter(pk=user.station_id)


class WeatherReadingViewSet(
    ScopedQuerysetMixin, BulkCreateMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.CreateModelMixin, viewsets.GenericViewSet,
):
    queryset = WeatherReading.objects.select_related("station")
    serializer_class = WeatherReadingSerializer


class PowerReadingViewSet(
    ScopedQuerysetMixin, BulkCreateMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.CreateModelMixin, viewsets.GenericViewSet,
):
    queryset = PowerReading.objects.select_related("station")
    serializer_class = PowerReadingSerializer


class IncidentViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Incident.objects.select_related("station", "reported_by")
    serializer_class = IncidentSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("open"):
            qs = qs.exclude(status=Incident.Status.RESOLVED)
        return qs

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)


class ItemViewSet(ScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Item.objects.select_related("station")
    serializer_class = ItemSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("low"):
            qs = qs.filter(quantity__lte=F("min_threshold"))
        return qs


@api_view(["GET"])
def live_status(request):
    """Latest reading per station - polled by the dashboard every minute."""
    user = request.user
    stations = Station.objects.all() if user.is_hq else Station.objects.filter(pk=user.station_id)
    data = []
    for st in stations:
        w, p = st.latest_weather, st.latest_power
        data.append({
            "id": st.pk,
            "code": st.code,
            "name": st.name,
            "weather": {
                "recorded_at": w.recorded_at,
                "temperature_c": w.temperature_c,
                "wind_speed_kmh": w.wind_speed_kmh,
                "pressure_hpa": w.pressure_hpa,
                "visibility_km": w.visibility_km,
            } if w else None,
            "power": {
                "recorded_at": p.recorded_at,
                "fuel_level_pct": p.fuel_level_pct,
                "load_kw": p.load_kw,
                "renewable_pct": p.renewable_pct,
                "battery_pct": p.battery_pct,
            } if p else None,
            "open_incidents": st.incidents.exclude(status=Incident.Status.RESOLVED).count(),
        })
    return Response({"generated_at": timezone.now(), "stations": data})
