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

    def get_readonly_fields(self, request, obj=None):
        # opening balance is set on creation; after that stock only changes through stock movements
        return ("quantity",) if obj else ()


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """Read-only audit trail. Corrections are made by recording a new, opposite movement."""

    list_display = ("created_at", "item", "kind", "quantity", "performed_by", "note")
    list_filter = ("kind", "item__station")
    search_fields = ("item__name", "note")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("reference", "station", "mode", "carrier", "departure_date", "eta", "status")
    list_filter = ("station", "mode", "status")
