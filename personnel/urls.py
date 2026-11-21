from django.urls import path

from . import views

app_name = "personnel"

urlpatterns = [
    path("members/", views.MemberList.as_view(), name="member_list"),
    path("members/new/", views.MemberCreate.as_view(), name="member_create"),
    path("members/<int:pk>/", views.MemberDetail.as_view(), name="member_detail"),
    path("members/<int:pk>/edit/", views.MemberUpdate.as_view(), name="member_edit"),
    path("expeditions/", views.ExpeditionList.as_view(), name="expedition_list"),
    path("expeditions/new/", views.ExpeditionCreate.as_view(), name="expedition_create"),
    path("expeditions/<int:pk>/", views.ExpeditionDetail.as_view(), name="expedition_detail"),
    path("expeditions/<int:pk>/edit/", views.ExpeditionUpdate.as_view(), name="expedition_edit"),
    path("medical/", views.MedicalList.as_view(), name="medical_list"),
    path("medical/new/", views.MedicalCreate.as_view(), name="medical_create"),
    path("medical/<int:pk>/", views.MedicalDetail.as_view(), name="medical_detail"),
    path("medical/<int:pk>/edit/", views.MedicalUpdate.as_view(), name="medical_edit"),
]
