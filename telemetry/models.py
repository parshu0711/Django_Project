from django.db import models
from django.utils import timezone


class WeatherReading(models.Model):
    class Source(models.TextChoices):
        AWS = "AWS", "Automatic weather station"
        MANUAL = "MANUAL", "Manual observation"

    station = models.ForeignKey("stations.Station", on_delete=models.CASCADE, related_name="weather_readings")
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    temperature_c = models.FloatField("temperature (°C)")
    wind_speed_kmh = models.FloatField("wind speed (km/h)")
    wind_direction_deg = models.PositiveSmallIntegerField("wind direction (°)", null=True, blank=True)
    pressure_hpa = models.FloatField("pressure (hPa)")
    humidity_pct = models.FloatField("humidity (%)", null=True, blank=True)
    visibility_km = models.FloatField("visibility (km)", null=True, blank=True)
    source = models.CharField(max_length=6, choices=Source.choices, default=Source.AWS)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["station", "-recorded_at"])]
        constraints = [
            models.UniqueConstraint(fields=["station", "recorded_at"], name="unique_weather_reading_per_time"),
        ]
        verbose_name = "weather reading"

    def __str__(self):
        return f"{self.station.code} {self.recorded_at:%d %b %H:%M} {self.temperature_c:.1f}°C"


class PowerReading(models.Model):
    station = models.ForeignKey("stations.Station", on_delete=models.CASCADE, related_name="power_readings")
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    generator_kw = models.FloatField("diesel generator (kW)", default=0)
    solar_kw = models.FloatField("solar (kW)", default=0)
    wind_kw = models.FloatField("wind turbine (kW)", default=0)
    load_kw = models.FloatField("station load (kW)", default=0)
    fuel_level_pct = models.FloatField("fuel tank level (%)")
    battery_pct = models.FloatField("battery charge (%)", null=True, blank=True)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["station", "-recorded_at"])]
        constraints = [
            models.UniqueConstraint(fields=["station", "recorded_at"], name="unique_power_reading_per_time"),
        ]
        verbose_name = "power reading"

    def __str__(self):
        return f"{self.station.code} {self.recorded_at:%d %b %H:%M} load {self.load_kw:.0f} kW"

    @property
    def total_generation_kw(self):
        return self.generator_kw + self.solar_kw + self.wind_kw

    @property
    def renewable_pct(self):
        total = self.total_generation_kw
        return round((self.solar_kw + self.wind_kw) / total * 100, 1) if total else 0.0
