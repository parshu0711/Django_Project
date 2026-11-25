"""DRF permission classes. Kept free of view imports: DRF loads them from settings while its views import."""
from rest_framework.permissions import BasePermission


class SensorScopePermission(BasePermission):
    """Sensor accounts may only upload telemetry; every other endpoint is closed to them."""

    message = "Sensor accounts can only upload telemetry readings."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not getattr(user, "is_sensor", False):
            return True
        return request.method == "POST" and getattr(view, "sensor_writable", False)
