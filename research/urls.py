from django.urls import path

from . import views

app_name = "research"

urlpatterns = [
    path("projects/", views.ProjectList.as_view(), name="project_list"),
    path("projects/new/", views.ProjectCreate.as_view(), name="project_create"),
    path("projects/<int:pk>/", views.ProjectDetail.as_view(), name="project_detail"),
    path("projects/<int:pk>/edit/", views.ProjectUpdate.as_view(), name="project_edit"),
    path("logs/", views.LogList.as_view(), name="log_list"),
    path("logs/new/", views.LogCreate.as_view(), name="log_create"),
    path("logs/<int:pk>/", views.LogDetail.as_view(), name="log_detail"),
    path("logs/<int:pk>/edit/", views.LogUpdate.as_view(), name="log_edit"),
]
