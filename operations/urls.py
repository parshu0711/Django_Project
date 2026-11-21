from django.urls import path

from . import views

app_name = "operations"

urlpatterns = [
    path("equipment/", views.EquipmentList.as_view(), name="equipment_list"),
    path("equipment/new/", views.EquipmentCreate.as_view(), name="equipment_create"),
    path("equipment/<int:pk>/", views.EquipmentDetail.as_view(), name="equipment_detail"),
    path("equipment/<int:pk>/edit/", views.EquipmentUpdate.as_view(), name="equipment_edit"),
    path("maintenance/", views.TaskList.as_view(), name="task_list"),
    path("maintenance/new/", views.TaskCreate.as_view(), name="task_create"),
    path("maintenance/<int:pk>/", views.TaskDetail.as_view(), name="task_detail"),
    path("maintenance/<int:pk>/edit/", views.TaskUpdate.as_view(), name="task_edit"),
    path("incidents/", views.IncidentList.as_view(), name="incident_list"),
    path("incidents/new/", views.IncidentCreate.as_view(), name="incident_create"),
    path("incidents/<int:pk>/", views.IncidentDetail.as_view(), name="incident_detail"),
    path("incidents/<int:pk>/edit/", views.IncidentUpdate.as_view(), name="incident_edit"),
]
