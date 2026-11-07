from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework import status

from apps.orders.models import Order
from apps.payments import paypal
from apps.payments.models import PaymentCheckout
from apps.payments.tests.base import PayPalTestCase

CLIENT = "apps.payments.services.paypal_client"

LINES = [
    {"name": "Black Hoodie", "quantity": 2, "unit_price": Decimal("49.00"), "sku": "HOOD-BLK-M"},
    {"name": "Cap", "quantity": 1, "unit_price": Decimal("12.50"), "sku": ""},
]


def build(**overrides) -> dict:
    """Run create_order against a fake PayPal and return the JSON body it would have sent."""
    sent: dict = {}

    def fake_request(method, path, *, json_body=None, headers=None):
        sent["body"] = json_body
        return {"id": "PP-1", "status": "CREATED", "links": []}

    arguments = dict(
        amount=Decimal("110.50"),
        currency="usd",
        return_url="https://app/pay/return?order=1&paypal=return",
        cancel_url="https://app/pay/return?order=1&paypal=cancel",
        custom_id="1",
        reference_id="ORD-1001",
        items=LINES,
        description="Demo Store - order ORD-1001",
        invoice_id="ORD-1001-AB12CD",
        brand_name="Demo Store",
    )
    arguments.update(overrides)
    with patch.object(paypal, "_request", side_effect=fake_request):
        paypal.create_order(**arguments)
    return sent["body"]


class CreateOrderPayloadTests(SimpleTestCase):
    def test_items_description_invoice_id_and_brand_reach_paypal(self):
        body = build()

        unit = body["purchase_units"][0]
        self.assertEqual(unit["amount"]["value"], "110.50")
        self.assertEqual(
            unit["amount"]["breakdown"], {"item_total": {"currency_code": "USD", "value": "110.50"}}
        )
        self.assertEqual(
            unit["items"],
            [
                {
                    "name": "Black Hoodie",
                    "quantity": "2",
                    "unit_amount": {"currency_code": "USD", "value": "49.00"},
                    "sku": "HOOD-BLK-M",
                },
                {
                    "name": "Cap",
                    "quantity": "1",
                    "unit_amount": {"currency_code": "USD", "value": "12.50"},
                },
            ],
        )
        self.assertEqual(unit["description"], "Demo Store - order ORD-1001")
        self.assertEqual(unit["invoice_id"], "ORD-1001-AB12CD")
        self.assertEqual(body["application_context"]["brand_name"], "Demo Store")
        self.assertEqual(body["application_context"]["user_action"], "PAY_NOW")

    def test_items_are_dropped_when_they_do_not_add_up_to_the_amount(self):
        unit = build(amount=Decimal("100.00"))["purchase_units"][0]

        self.assertNotIn("items", unit)
        self.assertNotIn("breakdown", unit["amount"])
        self.assertEqual(unit["amount"]["value"], "100.00")

    def test_items_are_dropped_when_any_price_is_zero(self):
        free = [*LINES, {"name": "Sticker", "quantity": 1, "unit_price": Decimal("0.00")}]

        unit = build(items=free)["purchase_units"][0]

        self.assertNotIn("items", unit)

    def test_works_without_the_optional_fields(self):
        unit = build(items=None, description="", invoice_id="", brand_name="")

        self.assertNotIn("items", unit["purchase_units"][0])
        self.assertNotIn("description", unit["purchase_units"][0])
        self.assertNotIn("invoice_id", unit["purchase_units"][0])
        self.assertNotIn("brand_name", unit["application_context"])

    def test_long_text_is_cut_to_paypals_limits(self):
        body = build(
            description="d" * 500,
            brand_name="Brand\n" + "b" * 500,
            items=[{"name": "n" * 500, "quantity": 1, "unit_price": Decimal("110.50")}],
        )

        unit = body["purchase_units"][0]
        self.assertEqual(len(unit["description"]), 127)
        self.assertEqual(len(unit["items"][0]["name"]), 127)
        self.assertEqual(len(body["application_context"]["brand_name"]), 127)
        self.assertNotIn("\n", body["application_context"]["brand_name"])


@override_settings(FRONTEND_URL="https://app.example.com")
class CreateCheckoutPayloadTests(PayPalTestCase):
    @patch(f"{CLIENT}.create_order")
    def test_checkout_describes_the_order_to_the_buyer(self, create_order):
        create_order.return_value = {
            "id": "PP-NEW",
            "status": "CREATED",
            "approve_url": "https://paypal.example/approve",
            "raw": {},
        }
        order_id = self.confirmed_order()

        response = self.client.post(
            f"/api/v1/payments/orders/{order_id}/checkout/", {}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(pk=order_id)
        kwargs = create_order.call_args.kwargs
        self.assertEqual(
            kwargs["items"],
            [
                {
                    "name": "Black Hoodie",
                    "quantity": 1,
                    "unit_price": Decimal("49.00"),
                    "sku": "HOOD-BLK-M",
                }
            ],
        )
        self.assertEqual(kwargs["description"], f"Demo Store - order {order.number}")
        self.assertEqual(kwargs["brand_name"], "Demo Store")
        self.assertRegex(kwargs["invoice_id"], rf"^{order.number}-[0-9A-F]{{6}}$")
        # A public landing page: the buyer paying from an emailed link has no Orbiz login.
        self.assertEqual(
            kwargs["return_url"],
            f"https://app.example.com/pay/return?order={order_id}&paypal=return",
        )
        self.assertEqual(
            kwargs["cancel_url"],
            f"https://app.example.com/pay/return?order={order_id}&paypal=cancel",
        )
        self.assertTrue(PaymentCheckout.objects.filter(order_id=order_id).exists())

    @patch(f"{CLIENT}.create_order")
    def test_each_checkout_gets_its_own_invoice_id(self, create_order):
        create_order.side_effect = [
            {"id": "PP-1", "status": "CREATED", "approve_url": "https://p/1", "raw": {}},
            {"id": "PP-2", "status": "CREATED", "approve_url": "https://p/2", "raw": {}},
        ]
        order_id = self.confirmed_order()

        for _ in range(2):
            self.client.post(f"/api/v1/payments/orders/{order_id}/checkout/", {}, format="json")

        first, second = (call.kwargs["invoice_id"] for call in create_order.call_args_list)
        self.assertNotEqual(first, second)
