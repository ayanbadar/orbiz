import uuid
from decimal import Decimal

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.customers.models import Customer
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
    PAYPAL_SUPPORTED_CURRENCIES=["USD"],
    FRONTEND_URL="http://localhost:5173",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)


@override_settings(**TEST_SETTINGS)
class PayPalTestCase(APITestCase):
    """A seller with a USD store, one customer, one $49 product, and helpers for PayPal flows."""

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
            store=self.store, name="Ayesha Khan", email="a@example.com"
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

    def confirmed_order(self) -> int:
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

    def paid_order(self, capture_id: str = "CAP-1") -> int:
        """A $49 order paid through a captured PayPal checkout."""
        order_id = self.confirmed_order()
        PaymentCheckout.objects.create(
            order_id=order_id,
            paypal_order_id=f"PP-{order_id}",
            status=PaymentCheckout.Status.CAPTURED,
            capture_id=capture_id,
            amount=Decimal("49.00"),
            currency="USD",
        )
        paid = self.client.post(f"/api/v1/orders/{order_id}/mark-paid/", {}, format="json")
        self.assertEqual(paid.status_code, status.HTTP_200_OK)
        return order_id

    def deliver(
        self, event_type: str, resource: dict, event_id: str | None = None
    ) -> PayPalWebhookEvent:
        """Store and process a (signature-verified) webhook event, as the Celery task would."""
        event_id = event_id or f"WH-{uuid.uuid4()}"
        event = receive_webhook(
            event_id=event_id,
            event_type=event_type,
            payload={"id": event_id, "event_type": event_type, "resource": resource},
        )
        process_webhook_event(event_pk=event.pk)
        event.refresh_from_db()
        return event
