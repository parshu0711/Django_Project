from django.contrib import admin

from .models import PowerReading, WeatherReading


@admin.register(WeatherReading)
class WeatherReadingAdmin(admin.ModelAdmin):
    list_display = ("recorded_at", "station", "temperature_c", "wind_speed_kmh", "pressure_hpa", "visibility_km", "source")
    list_filter = ("station", "source")
    date_hierarchy = "recorded_at"


@admin.register(PowerReading)
class PowerReadingAdmin(admin.ModelAdmin):
    list_display = ("recorded_at", "station", "generator_kw", "solar_kw", "wind_kw", "load_kw", "fuel_level_pct", "battery_pct")
    list_filter = ("station",)
    date_hierarchy = "recorded_at"
