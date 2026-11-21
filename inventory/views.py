from django.db.models import F

from core.mixins import CrudCreateView, CrudDetailView, CrudListView, CrudUpdateView

from .models import Item, Shipment, StockMovement

# -------------------------------------------------------------------- items


class ItemBase:
    model = Item
    url_base = "inventory:item"


class ItemList(ItemBase, CrudListView):
    title = "Stock items"
    subtitle = "Fuel, food, medical and spare-part stores at each station"
    related = ("station",)
    columns = (
        ("Item", "name"), ("Station", "station.name"), ("Category", "category"), ("In stock", "quantity"),
        ("Unit", "unit"), ("Minimum", "min_threshold"), ("Stock", "stock_status"), ("Location", "storage_location"),
    )
    badge_fields = ("stock_status",)
    search_fields = ("name", "storage_location")
    filter_fields = ("category",)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.GET.get("low"):
            qs = qs.filter(quantity__lte=F("min_threshold"))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.GET.get("low"):
            ctx["title"] = "Low-stock items"
        return ctx


class ItemCreate(ItemBase, CrudCreateView):
    fields = ["station", "name", "category", "unit", "quantity", "min_threshold", "storage_location"]


class ItemUpdate(ItemBase, CrudUpdateView):
    # quantity changes go through stock movements so there is an audit trail
    fields = ["station", "name", "category", "unit", "min_threshold", "storage_location"]


class ItemDetail(ItemBase, CrudDetailView):
    related = ({
        "title": "Stock movements",
        "attr": "movements",
        "columns": (("When", "created_at"), ("Movement", "kind"), ("Quantity", "quantity"),
                    ("Note", "note"), ("By", "performed_by")),
        "badge_fields": ("kind",),
        "add": ("inventory:movement_create", "item"),
    },)


# ---------------------------------------------------------------- movements


class MovementBase:
    model = StockMovement
    url_base = "inventory:movement"
    station_field = "item__station"


class MovementList(MovementBase, CrudListView):
    title = "Stock movements"
    subtitle = "Audit trail of every receipt and issue of stores"
    related = ("item", "item__station", "performed_by")
    columns = (
        ("When", "created_at"), ("Item", "item.name"), ("Station", "item.station"), ("Movement", "kind"),
        ("Quantity", "quantity"), ("Unit", "item.unit"), ("Note", "note"), ("By", "performed_by"),
    )
    badge_fields = ("kind",)
    search_fields = ("item__name", "note")
    filter_fields = ("kind",)


class MovementCreate(MovementBase, CrudCreateView):
    fields = ["item", "kind", "quantity", "note"]
    user_field = "performed_by"
    title = "Record stock movement"

    def get_success_url(self):
        return self.object.item.get_absolute_url()


# ---------------------------------------------------------------- shipments
SHIPMENT_FIELDS = [
    "reference", "station", "mode", "carrier", "origin", "departure_date", "eta", "status",
    "weight_tonnes", "cargo_summary",
]


class ShipmentBase:
    model = Shipment
    url_base = "inventory:shipment"


class ShipmentList(ShipmentBase, CrudListView):
    title = "Supply shipments"
    subtitle = "Ship, air and helicopter resupply to the stations"
    related = ("station",)
    columns = (
        ("Reference", "reference"), ("Station", "station"), ("Mode", "mode"), ("Carrier", "carrier"),
        ("From", "origin"), ("Departs", "departure_date"), ("ETA", "eta"), ("Status", "status"),
        ("Weight (t)", "weight_tonnes"),
    )
    badge_fields = ("status",)
    search_fields = ("reference", "carrier", "cargo_summary")
    filter_fields = ("mode", "status")


class ShipmentCreate(ShipmentBase, CrudCreateView):
    fields = SHIPMENT_FIELDS


class ShipmentUpdate(ShipmentBase, CrudUpdateView):
    fields = SHIPMENT_FIELDS


class ShipmentDetail(ShipmentBase, CrudDetailView):
    badge_fields = ("status",)
