from unittest.mock import patch

from rest_framework import status

from apps.assistant import services
from apps.assistant.tests.base import AssistantTestCase
from apps.orders.models import Order, OrderEvent


class DigestTests(AssistantTestCase):
    def test_digest_makes_zero_outbound_http_calls(self):
        self.confirmed_order()
        with patch("httpx.Client") as mock_client:
            result = services.digest(store=self.store)
        mock_client.assert_not_called()
        self.assertIn("stale_unpaid_orders", result)
        self.assertIn("low_stock_products", result)
        skus = [row["sku"] for row in result["low_stock_products"]]
        self.assertIn(self.low_stock_product.sku, skus)

    def test_digest_endpoint(self):
        response = self.client.get("/api/v1/assistant/digest/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("stale_unpaid_orders", response.data)


class ActivityTests(AssistantTestCase):
    def test_activity_filters_on_origin(self):
        self.confirmed_order()
        order = Order.objects.get(store=self.store)
        OrderEvent.objects.create(
            order=order, event_type=OrderEvent.EventType.NOTE, origin=OrderEvent.Origin.SELLER,
            message="Seller note.",
        )
        OrderEvent.objects.create(
            order=order, event_type=OrderEvent.EventType.NOTE, origin=OrderEvent.Origin.ASSISTANT,
            message="AI note.",
        )
        qs = services.activity_queryset(store=self.store)
        messages = [e.message for e in qs]
        self.assertIn("AI note.", messages)
        self.assertNotIn("Seller note.", messages)

    def test_activity_endpoint_scopes_to_store(self):
        self.confirmed_order()
        order = Order.objects.get(store=self.store)
        OrderEvent.objects.create(
            order=order, event_type=OrderEvent.EventType.NOTE, origin=OrderEvent.Origin.ASSISTANT,
            message="AI note.",
        )
        response = self.client.get("/api/v1/assistant/activity/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        messages = [row["message"] for row in response.data["results"]]
        self.assertIn("AI note.", messages)
