from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone


class Item(models.Model):
    class Category(models.TextChoices):
        FUEL = "FUEL", "Fuel & lubricants"
        FOOD = "FOOD", "Food & rations"
        MEDICAL = "MEDICAL", "Medical supplies"
        SPARES = "SPARES", "Spare parts"
        SCIENTIFIC = "SCIENTIFIC", "Scientific consumables"
        SAFETY = "SAFETY", "Safety & survival gear"
        GENERAL = "GENERAL", "General stores"

    station = models.ForeignKey("stations.Station", on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=12, choices=Category.choices, default=Category.GENERAL)
    unit = models.CharField(max_length=20, default="units", help_text="litres, kg, units, cylinders ...")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    min_threshold = models.DecimalField(
        "minimum stock level", max_digits=12, decimal_places=2, default=Decimal("0"),
        help_text="An alert is shown when stock falls to or below this level.",
    )
    storage_location = models.CharField(max_length=100, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["station__name", "category", "name"]
        unique_together = [("station", "name")]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="item_quantity_not_negative"),
        ]
        verbose_name = "stock item"

    def __str__(self):
        return f"{self.name} ({self.station.code})"

    def get_absolute_url(self):
        return reverse("inventory:item_detail", args=[self.pk])

    @property
    def is_low(self):
        return self.quantity <= self.min_threshold

    @property
    def stock_status(self):
        return "LOW" if self.is_low else "OK"


class StockMovement(models.Model):
    class Kind(models.TextChoices):
        IN = "IN", "Received (in)"
        OUT = "OUT", "Consumed / issued (out)"

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="movements")
    kind = models.CharField("movement", max_length=3, choices=Kind.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    note = models.CharField(max_length=255, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_movements"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "stock movement"

    def __str__(self):
        sign = "+" if self.kind == self.Kind.IN else "-"
        return f"{sign}{self.quantity} {self.item.unit} {self.item.name}"

    def _check_stock(self, item):
        if self.kind == self.Kind.OUT and self.quantity and self.quantity > item.quantity:
            raise ValidationError(
                {"quantity": f"Only {item.quantity.normalize():f} {item.unit} of {item.name} in stock."}
            )

    def clean(self):
        if self.item_id and self._state.adding:
            self._check_stock(self.item)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        with transaction.atomic():
            if is_new:
                # lock the item row so two simultaneous issues can't both pass the stock check
                self._check_stock(Item.objects.select_for_update().get(pk=self.item_id))
            super().save(*args, **kwargs)
            if is_new:
                delta = self.quantity if self.kind == self.Kind.IN else -self.quantity
                Item.objects.filter(pk=self.item_id).update(quantity=F("quantity") + delta, updated_at=timezone.now())


class Shipment(models.Model):
    class Mode(models.TextChoices):
        SHIP = "SHIP", "Ship (ice-class vessel)"
        AIR = "AIR", "Air (DROMLAN flight)"
        HELI = "HELI", "Helicopter sortie"
        LAND = "LAND", "Overland convoy"

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        IN_TRANSIT = "IN_TRANSIT", "In transit"
        DELAYED = "DELAYED", "Delayed"
        DELIVERED = "DELIVERED", "Delivered"

    reference = models.CharField(max_length=30, unique=True)
    station = models.ForeignKey("stations.Station", on_delete=models.CASCADE, related_name="shipments")
    mode = models.CharField(max_length=5, choices=Mode.choices, default=Mode.SHIP)
    carrier = models.CharField("vessel / carrier", max_length=120, blank=True)
    origin = models.CharField(max_length=100, default="Cape Town")
    departure_date = models.DateField(null=True, blank=True)
    eta = models.DateField("ETA", null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNED)
    weight_tonnes = models.DecimalField("weight (t)", max_digits=8, decimal_places=2, null=True, blank=True)
    cargo_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-departure_date"]

    def __str__(self):
        return self.reference

    def get_absolute_url(self):
        return reverse("inventory:shipment_detail", args=[self.pk])
