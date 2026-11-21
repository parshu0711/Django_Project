"""
Simulate the automatic weather station / power-plant feed for demos.

    python manage.py simulate_telemetry                 # one new reading per active station
    python manage.py simulate_telemetry --interval 30   # keep generating every 30 s (Ctrl+C to stop)
    python manage.py simulate_telemetry --storm BHA     # force a blizzard reading at Bharati

Readings are saved with normal save(), so the automatic alert rules run.
"""
import random
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from stations.models import Station
from telemetry.models import PowerReading, WeatherReading


class Command(BaseCommand):
    help = "Generate simulated live weather and power readings for active stations."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=0, help="Seconds between batches (0 = run once)")
        parser.add_argument("--storm", metavar="CODE", help="Station code to hit with a blizzard reading")

    def handle(self, *args, interval=0, storm=None, **options):
        try:
            while True:
                self._tick(storm)
                storm = None
                if not interval:
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write("\nStopped.")

    def _tick(self, storm):
        now = timezone.now()
        for st in Station.objects.filter(status=Station.Status.ACTIVE):
            w = st.latest_weather
            p = st.latest_power
            temp = (w.temperature_c if w else -8) + random.gauss(0, 0.8)
            wind = max(2.0, min(95.0, (w.wind_speed_kmh if w else 20) * 0.8 + 4 + random.gauss(0, 6)))
            if storm and storm.upper() == st.code:
                wind = random.uniform(115, 160)
            reading = WeatherReading.objects.create(
                station=st, recorded_at=now, temperature_c=round(temp, 1), wind_speed_kmh=round(wind, 1),
                wind_direction_deg=random.choice([90, 120, 135, 150]),
                pressure_hpa=round((w.pressure_hpa if w else 985) + random.gauss(0, 1), 1),
                humidity_pct=round(random.uniform(35, 80), 1),
                visibility_km=round(max(0.1, 20 - wind / 6), 1),
            )
            fuel = (p.fuel_level_pct if p else 60) - random.uniform(0.02, 0.08)
            solar = max(0.0, random.gauss(12, 5))
            load = random.gauss(84, 4)
            wind_kw = min(10.0, wind * 0.22) if wind < 90 else 0.0
            PowerReading.objects.create(
                station=st, recorded_at=now, generator_kw=round(max(25.0, load - solar - wind_kw), 1),
                solar_kw=round(solar, 1), wind_kw=round(wind_kw, 1), load_kw=round(load, 1),
                fuel_level_pct=round(fuel, 1), battery_pct=round(random.uniform(60, 95), 1),
            )
            self.stdout.write(
                f"{timezone.localtime(now):%H:%M:%S} {st.code}: {reading.temperature_c:+.1f} °C, "
                f"wind {reading.wind_speed_kmh:.0f} km/h, fuel {fuel:.1f}%"
            )
