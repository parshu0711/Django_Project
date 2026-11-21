from django.apps import AppConfig


class OperationsConfig(AppConfig):
    name = "operations"
    verbose_name = "Operations, equipment & incidents"

    def ready(self):
        from . import signals  # noqa: F401
