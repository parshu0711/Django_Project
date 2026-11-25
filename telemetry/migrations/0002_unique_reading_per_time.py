from django.db import migrations, models
from django.db.models import Count, Min


def remove_duplicate_readings(apps, schema_editor):
    """Keep the first copy of every (station, recorded_at) reading so the unique constraint can be added."""
    for name in ("WeatherReading", "PowerReading"):
        model = apps.get_model("telemetry", name)
        dupes = (
            model.objects.values("station_id", "recorded_at")
            .annotate(n=Count("id"), keep=Min("id"))
            .filter(n__gt=1)
        )
        for row in dupes:
            model.objects.filter(station_id=row["station_id"], recorded_at=row["recorded_at"]).exclude(
                pk=row["keep"]
            ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("stations", "0001_initial"),
        ("telemetry", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_readings, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="powerreading",
            constraint=models.UniqueConstraint(fields=("station", "recorded_at"), name="unique_power_reading_per_time"),
        ),
        migrations.AddConstraint(
            model_name="weatherreading",
            constraint=models.UniqueConstraint(
                fields=("station", "recorded_at"), name="unique_weather_reading_per_time"
            ),
        ),
    ]
