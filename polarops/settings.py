"""
Settings for PolarOps - Digital Platform for remote management of the
Indian Antarctic Research Stations (Maitri, Bharati, Dakshin Gangotri).

All environment-specific values come from a .env file (see .env.example).
"""
import os
import sys
import warnings
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name, default=None):
    return os.getenv(name, default)


def env_bool(name, default=False):
    return str(os.getenv(name, default)).strip().lower() in ("1", "true", "yes", "on")


DEV_SECRET_KEY = "dev-insecure-key-change-me-in-production"
SECRET_KEY = env("DJANGO_SECRET_KEY", DEV_SECRET_KEY)
DEBUG = env_bool("DJANGO_DEBUG", True)
TESTING = sys.argv[1:2] == ["test"]

if not DEBUG and not TESTING and SECRET_KEY in (DEV_SECRET_KEY, "change-me-to-a-long-random-string", ""):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set to a long random value when DJANGO_DEBUG is False. "
        "Generate one with: python -c \"from django.core.management.utils import get_random_secret_key as k; print(k())\""
    )
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # third party
    "rest_framework",
    "rest_framework.authtoken",
    # project apps
    "core",
    "accounts",
    "stations",
    "personnel",
    "inventory",
    "operations",
    "telemetry",
    "research",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "polarops.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.navigation",
                "core.context_processors.maps",
                "core.context_processors.demo",
                "core.context_processors.platform",
            ],
        },
    },
]

WSGI_APPLICATION = "polarops.wsgi.application"

# ---------------------------------------------------------------- database
if env("DB_ENGINE", "sqlite").lower() in ("postgres", "postgresql"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "polarops"),
            "USER": env("DB_USER", "postgres"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------ static files
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:landing"

from django.contrib.messages import constants as message_constants  # noqa: E402

MESSAGE_TAGS = {message_constants.ERROR: "danger"}

# ---------------------------------------------------------------- REST API
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "core.permissions.SensorScopePermission",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "user": env("API_RATE_USER", "600/min"),
        "token": env("API_RATE_TOKEN", "10/min"),   # POST /api/auth/token/ - slows password guessing
    },
}

# ------------------------------------------------------------------- email
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "PolarOps Alerts <alerts@polarops.local>")
# Seconds before giving up on the mail server, so a dead SMTP link never hangs a request.
EMAIL_TIMEOUT = int(env("EMAIL_TIMEOUT", "10"))

# --------------------------------------------------- automatic alert rules
POLAROPS_ALERTS = {
    "WIND_KMH": float(env("ALERT_WIND_KMH", "100")),
    "TEMP_C": float(env("ALERT_TEMP_C", "-45")),
    "VISIBILITY_KM": float(env("ALERT_VISIBILITY_KM", "0.2")),
    "FUEL_PCT": float(env("ALERT_FUEL_PCT", "20")),
    "BATTERY_PCT": float(env("ALERT_BATTERY_PCT", "15")),
    "DEDUPE_HOURS": 6,
}

# --------------------------------------------------------------- demo mode
# One-click switching between the seeded demo accounts (profile menu + login page).
# Follows DEBUG unless set explicitly. NEVER enable on a real deployment.
DEMO_MODE = env_bool("DEMO_MODE", DEBUG)

# -------------------------------------------------------------------- maps
# Browser key for the Google Maps JavaScript API. Empty = use OpenStreetMap via Leaflet.
GOOGLE_MAPS_API_KEY = env("GOOGLE_MAPS_API_KEY", "").strip()

# ----------------------------------------------------------------- logging
# Alert creation and mail failures are logged; LOG_FILE adds a file next to the console output.
LOG_LEVEL = env("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        name: {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False}
        for name in ("operations", "telemetry", "core")
    },
}
if env("LOG_FILE"):
    LOGGING["handlers"]["file"] = {"class": "logging.FileHandler", "filename": env("LOG_FILE"), "formatter": "plain"}
    for logger in (LOGGING["root"], *LOGGING["loggers"].values()):
        logger["handlers"].append("file")

# ------------------------------------------------------------------- tests
if TESTING:
    # the default hasher is deliberately slow; tests create many users
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    warnings.filterwarnings("ignore", message="No directory at", category=UserWarning)
    LOGGING["loggers"] = {}   # keep test output clean
    LOGGING["root"]["level"] = "CRITICAL"

# -------------------------------------------------------- HTTPS / production
SESSION_COOKIE_HTTPONLY = True
if not DEBUG and not TESTING:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "0"))   # e.g. 31536000 once HTTPS is confirmed working
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_REFERRER_POLICY = "same-origin"
    if env_bool("BEHIND_HTTPS_PROXY", False):   # nginx / load balancer terminates TLS
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
