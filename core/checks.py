"""System checks that stop PolarOps from running with unsafe settings."""
from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def demo_mode_check(app_configs, **kwargs):
    # the test runner forces DEBUG=False, so test runs are exempt
    if settings.DEMO_MODE and not settings.DEBUG and not getattr(settings, "TESTING", False):
        return [
            Error(
                "DEMO_MODE is on while DJANGO_DEBUG is False.",
                hint="Demo mode lets anyone sign in as the HQ administrator without a password. "
                     "Set DEMO_MODE=False in .env for any real deployment.",
                id="polarops.E001",
            )
        ]
    return []


@register(deploy=True)
def email_check(app_configs, **kwargs):
    if settings.EMAIL_BACKEND.endswith("console.EmailBackend"):
        return [
            Warning(
                "Incident alert emails use the console backend, so they are only printed, never delivered.",
                hint="Set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend and the SMTP settings in .env.",
                id="polarops.W001",
            )
        ]
    return []
