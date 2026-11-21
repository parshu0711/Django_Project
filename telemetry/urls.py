from django.urls import path

from . import views

app_name = "telemetry"

urlpatterns = [
    path("weather/", views.WeatherList.as_view(), name="weather_list"),
    path("weather/new/", views.WeatherCreate.as_view(), name="weather_create"),
    path("power/", views.PowerList.as_view(), name="power_list"),
    path("power/new/", views.PowerCreate.as_view(), name="power_create"),
]
