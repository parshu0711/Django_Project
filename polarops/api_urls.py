from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core import api

router = DefaultRouter()
router.register("stations", api.StationViewSet)
router.register("weather", api.WeatherReadingViewSet)
router.register("power", api.PowerReadingViewSet)
router.register("incidents", api.IncidentViewSet)
router.register("inventory", api.ItemViewSet)

urlpatterns = [
    path("live/", api.live_status, name="api-live"),
    path("auth/token/", api.ObtainTokenView.as_view(), name="api-token"),
    path("", include(router.urls)),
]
