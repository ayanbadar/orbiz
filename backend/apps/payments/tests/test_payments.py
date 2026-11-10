import json
from decimal import Decimal
from unittest.mock import patch

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.orders.models import Order, OrderEvent
from apps.payments.models import PaymentCheckout, PayPalWebhookEvent
from apps.payments.services import process_webhook_event, receive_webhook
from apps.products.models import Product
from apps.stores.services import create_store_for_user

PASSWORD = "Orb1z-pass"

TEST_SETTINGS = dict(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PAYPAL_CLIENT_ID="test-client",
    PAYPAL_CLIENT_SECRET="test-secret",
    PAYPAL_MODE="sandbox",
    PAYPAL_WEBHOOK_ID="WH-test",
    FRONTEND_URL="http://localhost:5173",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)


@override_settings(**TEST_SETTINGS)
class PaymentApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="seller@example.com", password=PASSWORD, first_name="S"
        )
        self.other = User.objects.create_user(
            email="other@example.com", password=PASSWORD, first_name="O"
        )
        self.store = create_store_for_user(
            user=self.user,
            name="Demo Store",
            currency="USD",
            timezone="UTC",
            business_type="social",
        )
        create_store_for_user(
            user=self.other,
            name="Other Store",
            currency="USD",
            timezone="UTC",
            business_type="social",
        )
        self.customer = Customer.objects.create(
            store=self.store, name="Ayesha", email="a@example.com"
        )
        self.product = Product.objects.create(
            store=self.store,
            name="Black Hoodie",
            sku="HOOD-BLK-M",
            price=Decimal("49.00"),
            currency="USD",
            stock_quantity=10,
        )
        self.client.force_authenticate(self.user)

    def _confirmed_order(self):
        created = self.client.post(
            "/api/v1/orders/",
            {
                "customer_id": self.customer.id,
                "lines": [{"product_id": self.product.id, "quantity": 1}],
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        order_id = created.data["id"]
        confirmed = self.client.post(
            f"/api/v1/orders/{order_id}/confirm/", {}, format="json"
        )
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK)
        return order_id

    @patch("apps.payments.services.paypal_client.create_order")
    def test_create_checkout_happy_path(self, mock_create):
        mock_create.return_value = {
            "id": "PAYPAL-ORDER-1",
            "status": "CREATED",
            "approve_url": "https://www.sandbox.paypal.com/checkoutnow?token=PAYPAL-ORDER-1",
            "raw": {},
        }
        order_id = self._confirmed_order()
        response = self.client.post(
            f"/api/v1/payments/orders/{order_id}/checkout/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["paypal_order_id"], "PAYPAL-ORDER-1")
        self.assertEqual(response.data["status"], "created")
        self.assertTrue(response.data["approve_url"])
        self.assertTrue(response.data["is_sandbox"])
        self.assertTrue(
            PaymentCheckout.objects.filter(
                order_id=order_id, paypal_order_id="PAYPAL-ORDER-1"
            ).exists()
        )
        detail = self.client.get(f"/api/v1/orders/{order_id}/")
        self.assertEqual(detail.data["paypal_checkout"]["paypal_order_id"], "PAYPAL-ORDER-1")
        self.assertTrue(detail.data["paypal_configured"])
        self.assertTrue(detail.data["paypal_sandbox"])

    @patch("apps.payments.services.paypal_client.create_order")
    def test_create_checkout_wrong_store_404(self, mock_create):
        mock_create.return_value = {
            "id": "PAYPAL-ORDER-1",
            "status": "CREATED",
            "approve_url": "https://example.com/approve",
            "raw": {},
        }
        order_id = self._confirmed_order()
        self.client.force_authenticate(self.other)
        response = self.client.post(
            f"/api/v1/payments/orders/{order_id}/checkout/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_create.assert_not_called()

    @patch("apps.payments.services.paypal_client.create_order")
    def test_create_checkout_already_paid_409(self, mock_create):
        order_id = self._confirmed_order()
        paid = self.client.post(f"/api/v1/orders/{order_id}/mark-paid/", {}, format="json")
        self.assertEqual(paid.status_code, status.HTTP_200_OK)
        response = self.client.post(
            f"/api/v1/payments/orders/{order_id}/checkout/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        mock_create.assert_not_called()

    @override_settings(PAYPAL_CLIENT_ID="", PAYPAL_CLIENT_SECRET="")
    def test_create_checkout_unconfigured_503(self):
        order_id = self._confirmed_order()
        response = self.client.post(
            f"/api/v1/payments/orders/{order_id}/checkout/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @patch("apps.payments.services.paypal_client.capture_order")
    @patch("apps.payments.services.paypal_client.create_order")
    def test_capture_marks_paid_once(self, mock_create, mock_capture):
        mock_create.return_value = {
            "id": "PAYPAL-ORDER-2",
            "status": "CREATED",
            "approve_url": "https://example.com/approve",
            "raw": {},
        }
        mock_capture.return_value = {
            "id": "PAYPAL-ORDER-2",
            "status": "COMPLETED",
            "capture_id": "CAPTURE-1",
            "capture_status": "COMPLETED",
            "raw": {},
        }
        order_id = self._confirmed_order()
        self.client.post(
            f"/api/v1/payments/orders/{order_id}/checkout/", {}, format="json"
        )
        captured = self.client.post(
            f"/api/v1/payments/orders/{order_id}/capture/", {}, format="json"
        )
        self.assertEqual(captured.status_code, status.HTTP_200_OK)
        self.assertEqual(captured.data["payment_status"], "paid")
        checkout = PaymentCheckout.objects.get(paypal_order_id="PAYPAL-ORDER-2")
        self.assertEqual(checkout.status, PaymentCheckout.Status.CAPTURED)
        self.assertEqual(checkout.capture_id, "CAPTURE-1")

        again = self.client.post(
            f"/api/v1/payments/orders/{order_id}/capture/", {}, format="json"
        )
        self.assertEqual(again.status_code, status.HTTP_200_OK)
        self.assertEqual(again.data["payment_status"], "paid")
        self.assertEqual(mock_capture.call_count, 1)

    @patch("apps.payments.services.paypal_client.capture_order")
    @patch("apps.payments.services.paypal_client.create_order")
    def test_capture_failure_sets_failed(self, mock_create, mock_capture):
        from apps.common.exceptions import BadGatewayError

        mock_create.return_value = {
            "id": "PAYPAL-ORDER-3",
            "status": "CREATED",
            "approve_url": "https://example.com/approve",
            "raw": {},
        }
        mock_capture.side_effect = BadGatewayError("PayPal rejected the payment request.")
        order_id = self._confirmed_order()
        self.client.post(
            f"/api/v1/payments/orders/{order_id}/checkout/", {}, format="json"
        )
        response = self.client.post(
            f"/api/v1/payments/orders/{order_id}/capture/", {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.payment_status, Order.PaymentStatus.FAILED)
        self.assertTrue(
            OrderEvent.objects.filter(
                order_id=order_id,
                event_type=OrderEvent.EventType.PAYMENT_STATUS_CHANGED,
                to_value=Order.PaymentStatus.FAILED,
            ).exists()
        )

    @patch("apps.payments.views.paypal_client.verify_webhook", return_value=False)
    def test_webhook_invalid_signature_rejected(self, _mock_verify):
        response = self.client.post(
            "/api/v1/payments/webhooks/paypal/",
            data=json.dumps({"id": "WH-EVT-1", "event_type": "PAYMENT.CAPTURE.COMPLETED"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PayPalWebhookEvent.objects.count(), 0)

    @patch("apps.payments.views.paypal_client.verify_webhook", return_value=True)
    def test_webhook_pays_once_and_duplicate_noop(self, _mock_verify):
        order_id = self._confirmed_order()
        PaymentCheckout.objects.create(
            order_id=order_id,
            paypal_order_id="PAYPAL-ORDER-WH",
            status=PaymentCheckout.Status.CREATED,
            approve_url="https://example.com/approve",
            amount=Decimal("49.00"),
            currency="USD",
            is_sandbox=True,
        )
        payload = {
            "id": "WH-EVT-PAID",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "id": "CAPTURE-WH-1",
                "status": "COMPLETED",
                "custom_id": str(order_id),
                "supplementary_data": {
                    "related_ids": {"order_id": "PAYPAL-ORDER-WH"},
                },
            },
        }
        # Run on_commit callbacks immediately (TestCase wraps tests in a transaction).
        with patch(
            "apps.payments.views.transaction.on_commit",
            side_effect=lambda fn: fn(),
        ), patch(
            "apps.payments.views.process_paypal_webhook_event.delay",
            side_effect=lambda event_pk: process_webhook_event(event_pk=event_pk),
        ):
            response = self.client.post(
                "/api/v1/payments/webhooks/paypal/",
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = PayPalWebhookEvent.objects.get(event_id="WH-EVT-PAID")
        self.assertIsNotNone(event.processed_at)
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)

        # Duplicate delivery: same event id, already processed — no second paid event.
        with patch(
            "apps.payments.views.transaction.on_commit",
            side_effect=lambda fn: fn(),
        ), patch(
            "apps.payments.views.process_paypal_webhook_event.delay"
        ) as mock_delay:
            again = self.client.post(
                "/api/v1/payments/webhooks/paypal/",
                data=json.dumps(payload),
                content_type="application/json",
            )
        self.assertEqual(again.status_code, status.HTTP_200_OK)
        self.assertEqual(PayPalWebhookEvent.objects.filter(event_id="WH-EVT-PAID").count(), 1)
        mock_delay.assert_not_called()
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        paid_events = OrderEvent.objects.filter(
            order_id=order_id,
            event_type=OrderEvent.EventType.PAYMENT_STATUS_CHANGED,
            to_value=Order.PaymentStatus.PAID,
        )
        self.assertEqual(paid_events.count(), 1)

    def test_receive_webhook_duplicate_returns_existing(self):
        first = receive_webhook(
            event_id="WH-DUP",
            event_type="PAYMENT.CAPTURE.COMPLETED",
            payload={"id": "WH-DUP"},
        )
        second = receive_webhook(
            event_id="WH-DUP",
            event_type="PAYMENT.CAPTURE.COMPLETED",
            payload={"id": "WH-DUP"},
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(PayPalWebhookEvent.objects.count(), 1)
