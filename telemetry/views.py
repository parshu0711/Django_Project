from core.mixins import CrudCreateView, CrudListView

from .models import PowerReading, WeatherReading


class WeatherList(CrudListView):
    model = WeatherReading
    url_base = "telemetry:weather"
    title = "Weather readings"
    subtitle = "Automatic weather station feed and manual observations"
    paginate_by = 50
    related = ("station",)
    columns = (
        ("Recorded", "recorded_at"), ("Station", "station"), ("Temp °C", "temperature_c"),
        ("Wind km/h", "wind_speed_kmh"), ("Dir °", "wind_direction_deg"), ("Pressure hPa", "pressure_hpa"),
        ("Humidity %", "humidity_pct"), ("Visibility km", "visibility_km"), ("Source", "source"),
    )
    filter_fields = ("source",)


class WeatherCreate(CrudCreateView):
    model = WeatherReading
    url_base = "telemetry:weather"
    title = "Log a manual weather observation"
    fields = [
        "station", "recorded_at", "temperature_c", "wind_speed_kmh", "wind_direction_deg",
        "pressure_hpa", "humidity_pct", "visibility_km", "source",
    ]

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault("source", WeatherReading.Source.MANUAL)
        return initial


class PowerList(CrudListView):
    model = PowerReading
    url_base = "telemetry:power"
    title = "Power & fuel readings"
    subtitle = "Generator, renewable output, load and fuel reserve"
    paginate_by = 50
    related = ("station",)
    columns = (
        ("Recorded", "recorded_at"), ("Station", "station"), ("Generator kW", "generator_kw"),
        ("Solar kW", "solar_kw"), ("Wind kW", "wind_kw"), ("Load kW", "load_kw"),
        ("Renewable %", "renewable_pct"), ("Fuel %", "fuel_level_pct"), ("Battery %", "battery_pct"),
    )


class PowerCreate(CrudCreateView):
    model = PowerReading
    url_base = "telemetry:power"
    title = "Log a power reading"
    fields = ["station", "recorded_at", "generator_kw", "solar_kw", "wind_kw", "load_kw", "fuel_level_pct", "battery_pct"]
