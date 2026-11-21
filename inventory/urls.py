from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("items/", views.ItemList.as_view(), name="item_list"),
    path("items/new/", views.ItemCreate.as_view(), name="item_create"),
    path("items/<int:pk>/", views.ItemDetail.as_view(), name="item_detail"),
    path("items/<int:pk>/edit/", views.ItemUpdate.as_view(), name="item_edit"),
    path("movements/", views.MovementList.as_view(), name="movement_list"),
    path("movements/new/", views.MovementCreate.as_view(), name="movement_create"),
    path("shipments/", views.ShipmentList.as_view(), name="shipment_list"),
    path("shipments/new/", views.ShipmentCreate.as_view(), name="shipment_create"),
    path("shipments/<int:pk>/", views.ShipmentDetail.as_view(), name="shipment_detail"),
    path("shipments/<int:pk>/edit/", views.ShipmentUpdate.as_view(), name="shipment_edit"),
]
