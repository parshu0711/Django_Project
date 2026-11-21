from django.contrib import admin

from .models import Item, Shipment, StockMovement


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "station", "category", "quantity", "unit", "min_threshold", "is_low")
    list_filter = ("station", "category")
    search_fields = ("name",)

    @admin.display(boolean=True, description="Low stock")
    def is_low(self, obj):
        return obj.is_low


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "item", "kind", "quantity", "performed_by", "note")
    list_filter = ("kind", "item__station")


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("reference", "station", "mode", "carrier", "departure_date", "eta", "status")
    list_filter = ("station", "mode", "status")
