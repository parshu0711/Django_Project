import datetime
from decimal import Decimal

from django import template
from django.db import models
from django.template.defaultfilters import linebreaksbr
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import capfirst

register = template.Library()

BADGE_COLOURS = {
    # red
    "CRITICAL": "danger", "RED": "danger", "FAULTY": "danger", "DELAYED": "danger",
    "LOW": "danger", "OVERDUE": "danger", "OPEN": "danger",
    # amber
    "HIGH": "warning", "AMBER": "warning", "MAINTENANCE": "warning", "IN_TRANSIT": "warning",
    "ACKNOWLEDGED": "warning", "ON_HOLD": "warning", "SEASONAL": "warning", "DUE_SOON": "warning",
    # blue
    "MEDIUM": "info", "IN_PROGRESS": "info", "PLANNED": "info", "PROPOSED": "info",
    "ON_FIELD": "info", "STANDBY": "info", "OUT": "info",
    # green
    "GREEN": "success", "OPERATIONAL": "success", "DONE": "success", "RESOLVED": "success",
    "DELIVERED": "success", "ACTIVE": "success", "ON_STATION": "success", "COMPLETED": "success",
    "OK": "success", "IN": "success",
}

# priorities / severities use "LOW" too, but low priority should not be red
SOFT_LOW_FIELDS = {"priority", "severity"}


def resolve(obj, accessor):
    """Return (display value, raw value) for a dotted accessor, using get_FOO_display for choices."""
    value = obj
    parts = accessor.split(".")
    for i, part in enumerate(parts):
        if value is None:
            return None, None
        if i == len(parts) - 1:
            display = getattr(value, f"get_{part}_display", None)
            if callable(display):
                return display(), getattr(value, part)
        value = getattr(value, part, None)
        if callable(value) and not isinstance(value, models.Manager):
            value = value()
    return value, value


def format_value(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime("%d %b %Y, %H:%M")
    if isinstance(value, datetime.date):
        return value.strftime("%d %b %Y")
    if isinstance(value, float):
        return f"{value:,.1f}"
    if isinstance(value, Decimal):
        text = f"{value:,.2f}"
        return text.rstrip("0").rstrip(".") if "." in text else text
    return str(value)


@register.filter
def badge_colour(value, field=""):
    value = str(value)
    if value == "LOW" and field.split(".")[-1] in SOFT_LOW_FIELDS:
        return "secondary"
    return BADGE_COLOURS.get(value, "secondary")


@register.simple_tag
def cell(obj, accessor, badge_fields=(), link=None):
    display, raw = resolve(obj, accessor)
    if isinstance(raw, bool):
        return format_html('<span class="bool {}">{}</span>', "yes" if raw else "no", "Yes" if raw else "No")
    text = format_value(display)
    if accessor in badge_fields and raw not in (None, ""):
        html = format_html('<span class="tag tag-{}">{}</span>', badge_colour(raw, accessor), text)
    else:
        html = format_html("{}", text)
    if link:
        html = format_html('<a href="{}" class="row-link">{}</a>', link, html)
    return html


@register.simple_tag
def object_fields(obj, badge_fields=(), exclude=()):
    """Rows of (label, html, wide) describing every concrete field of a model instance."""
    rows = []
    for field in obj._meta.fields:
        if field.name in ("id",) or field.name in exclude:
            continue
        display, raw = resolve(obj, field.name)
        wide = isinstance(field, models.TextField)
        if isinstance(raw, bool):
            html = cell(obj, field.name)
        elif wide and raw:
            html = linebreaksbr(raw, autoescape=True)
        elif field.name in badge_fields and raw:
            html = format_html('<span class="tag tag-{}">{}</span>', badge_colour(raw, field.name), display)
        elif isinstance(raw, models.Model) and hasattr(raw, "get_absolute_url"):
            html = format_html('<a href="{}">{}</a>', raw.get_absolute_url(), raw)
        else:
            html = format_value(display)
        rows.append((capfirst(field.verbose_name), html, wide))
    return rows


@register.simple_tag(takes_context=True)
def active(context, *prefixes):
    match = getattr(context.get("request"), "resolver_match", None)
    if match and any(match.view_name.startswith(p) for p in prefixes):
        return "active"
    return ""


@register.filter
def pct_class(value, reverse=False):
    """Colour for a percentage gauge: low = red unless reverse."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "secondary"
    if reverse:
        value = 100 - value
    if value <= 20:
        return "danger"
    if value <= 40:
        return "warning"
    return "success"


@register.filter
def get_item(mapping, key):
    return mapping.get(key) if mapping else None


@register.simple_tag
def wind_dir(deg):
    try:
        deg = float(deg)
    except (TypeError, ValueError):
        return ""
    points = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return points[int((deg % 360) / 45 + 0.5) % 8]


@register.filter
def ago(value):
    if not value:
        return "never"
    delta = timezone.now() - value
    mins = int(delta.total_seconds() // 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins} min ago"
    hours = mins // 60
    if hours < 48:
        return f"{hours} h ago"
    return f"{hours // 24} days ago"



@register.simple_tag
def station_points(station=None):
    """Public station facts for the wireframe globe (login page, station header).

    Only names, codes, coordinates, status and founding year: never operational data.
    """
    from stations.models import Station

    stations = [station] if station is not None else Station.objects.all()
    return [
        {
            "name": s.name,
            "code": s.code,
            "lat": float(s.latitude),
            "lng": float(s.longitude),
            "status": s.status,
            "status_label": s.get_status_display(),
            "established": s.established,
        }
        for s in stations
    ]


@register.filter
def dms(value, axis="lat"):
    """Decimal degrees -> 70°46′S style. axis is "lat" or "lng"."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    a = abs(v)
    d, m = int(a), round((a - int(a)) * 60)
    if m == 60:
        d, m = d + 1, 0
    hemi = ("S" if v < 0 else "N") if axis == "lat" else ("W" if v < 0 else "E")
    return f"{d}°{m:02d}′{hemi}"
