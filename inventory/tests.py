"""Stock levels, the movement audit trail and the no-negative-stock rule."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.testing import PolarFixtures

from .models import StockMovement


class StockMovementTests(PolarFixtures, TestCase):
    def move(self, kind, qty, item=None):
        return StockMovement.objects.create(item=item or self.mai_diesel, kind=kind, quantity=Decimal(qty))

    def test_receipt_increases_stock(self):
        self.move(StockMovement.Kind.IN, "250")
        self.mai_diesel.refresh_from_db()
        self.assertEqual(self.mai_diesel.quantity, Decimal("750"))

    def test_issue_decreases_stock(self):
        self.move(StockMovement.Kind.OUT, "120.5")
        self.mai_diesel.refresh_from_db()
        self.assertEqual(self.mai_diesel.quantity, Decimal("379.5"))

    def test_editing_a_movement_does_not_change_stock_twice(self):
        movement = self.move(StockMovement.Kind.IN, "10")
        movement.note = "corrected note"
        movement.save()
        self.mai_diesel.refresh_from_db()
        self.assertEqual(self.mai_diesel.quantity, Decimal("510"))

    def test_over_issue_fails_validation(self):
        movement = StockMovement(item=self.mai_diesel, kind=StockMovement.Kind.OUT, quantity=Decimal("501"))
        with self.assertRaises(ValidationError) as ctx:
            movement.full_clean()
        self.assertIn("Only 500 litres", str(ctx.exception))

    def test_zero_quantity_is_invalid(self):
        movement = StockMovement(item=self.mai_diesel, kind=StockMovement.Kind.IN, quantity=Decimal("0"))
        with self.assertRaises(ValidationError):
            movement.full_clean()

    def test_low_stock_flag(self):
        self.assertTrue(self.bha_rice.is_low)
        self.assertEqual(self.bha_rice.stock_status, "LOW")
        self.assertFalse(self.mai_diesel.is_low)


class StockMovementFormTests(PolarFixtures, TestCase):
    def post(self, **data):
        return self.client.post(reverse("inventory:movement_create"), {"item": self.mai_diesel.pk, "note": "", **data})

    def test_issue_through_form_records_user_and_redirects_to_item(self):
        self.login(self.mai_leader)
        response = self.post(kind="OUT", quantity="100")
        self.assertRedirects(response, self.mai_diesel.get_absolute_url())
        self.mai_diesel.refresh_from_db()
        self.assertEqual(self.mai_diesel.quantity, Decimal("400"))
        self.assertEqual(StockMovement.objects.get().performed_by, self.mai_leader)

    def test_form_rejects_over_issue(self):
        self.login(self.mai_leader)
        response = self.post(kind="OUT", quantity="9999")
        self.assertEqual(response.status_code, 200)
        self.assertIn("quantity", response.context["form"].errors)
        self.mai_diesel.refresh_from_db()
        self.assertEqual(self.mai_diesel.quantity, Decimal("500"))

    def test_station_staff_cannot_move_other_station_stock(self):
        self.login(self.mai_leader)
        response = self.client.post(reverse("inventory:movement_create"),
                                    {"item": self.bha_rice.pk, "kind": "IN", "quantity": "10"})
        self.assertIn("item", response.context["form"].errors)
        self.bha_rice.refresh_from_db()
        self.assertEqual(self.bha_rice.quantity, Decimal("5"))

    def test_quantity_cannot_be_edited_directly(self):
        self.login(self.hq)
        form = self.client.get(reverse("inventory:item_edit", args=[self.mai_diesel.pk])).context["form"]
        self.assertNotIn("quantity", form.fields)

    def test_movement_list_is_scoped(self):
        StockMovement.objects.create(item=self.bha_rice, kind="IN", quantity=Decimal("1"))
        StockMovement.objects.create(item=self.mai_diesel, kind="IN", quantity=Decimal("1"))
        self.login(self.mai_leader)
        rows = self.client.get(reverse("inventory:movement_list")).context["object_list"]
        self.assertEqual([m.item for m in rows], [self.mai_diesel])
