from django.urls import path

from . import views

app_name = "stations"

urlpatterns = [
    path("", views.StationList.as_view(), name="station_list"),
    path("new/", views.StationCreate.as_view(), name="station_create"),
    path("<int:pk>/", views.StationDetail.as_view(), name="station_detail"),
    path("<int:pk>/edit/", views.StationUpdate.as_view(), name="station_edit"),
    path("sitreps/", views.SitRepList.as_view(), name="sitrep_list"),
    path("sitreps/new/", views.SitRepCreate.as_view(), name="sitrep_create"),
    path("sitreps/<int:pk>/", views.SitRepDetail.as_view(), name="sitrep_detail"),
    path("sitreps/<int:pk>/edit/", views.SitRepUpdate.as_view(), name="sitrep_edit"),
]
