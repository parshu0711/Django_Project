from django.apps import AppConfig


class TelemetryConfig(AppConfig):
    name = "telemetry"
    verbose_name = "Telemetry (weather & power)"

    def ready(self):
        from . import signals  # noqa: F401
