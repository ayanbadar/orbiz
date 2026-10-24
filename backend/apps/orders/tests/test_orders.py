from decimal import Decimal

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.products.models import InventoryAdjustment, Product
from apps.stores.services import create_store_for_user

PASSWORD = "Orb1z-pass"

TEST_SETTINGS = dict(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)


@override_settings(**TEST_SETTINGS)
class OrderApiTests(APITestCase):
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
        self.other_store = create_store_for_user(
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

    def _create_draft(self, quantity=2):
        return self.client.post(
            "/api/v1/orders/",
            {
                "customer_id": self.customer.id,
                "delivery_notes": "Clifton",
                "lines": [{"product_id": self.product.id, "quantity": quantity}],
            },
            format="json",
        )

    def test_unauthenticated_rejected(self):
        response = self.client.get("/api/v1/orders/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_list_and_scope(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["fulfilment_status"], "draft")
        self.assertEqual(created.data["payment_status"], "unpaid")
        self.assertEqual(len(created.data["lines"]), 1)
        self.assertTrue(created.data["number"].startswith("ORD-"))

        listed = self.client.get("/api/v1/orders/")
        self.assertIn("results", listed.data)
        results = listed.data["results"]
        self.assertEqual(len(results), 1)

        self.client.force_authenticate(self.other)
        other_list = self.client.get("/api/v1/orders/")
        self.assertIn("results", other_list.data)
        self.assertEqual(len(other_list.data["results"]), 0)
        foreign = self.client.get(f"/api/v1/orders/{created.data['id']}/")
        self.assertEqual(foreign.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_lines_rejected(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/orders/",
            {"customer_id": self.customer.id, "lines": []},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_deducts_stock(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft(quantity=3)
        order_id = created.data["id"]
        confirmed = self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK)
        self.assertEqual(confirmed.data["fulfilment_status"], "unfulfilled")
        self.assertEqual(confirmed.data["payment_status"], "pending")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)
        self.assertTrue(
            InventoryAdjustment.objects.filter(
                product=self.product, reason=f"sale:{confirmed.data['number']}"
            ).exists()
        )

    def test_confirm_oversell_blocked(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft(quantity=50)
        order_id = created.data["id"]
        bad = self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.fulfilment_status, Order.FulfilmentStatus.DRAFT)

    def test_cancel_restores_stock(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft(quantity=2)
        order_id = created.data["id"]
        self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        cancelled = self.client.post(f"/api/v1/orders/{order_id}/cancel/", {}, format="json")
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK)
        self.assertEqual(cancelled.data["fulfilment_status"], "cancelled")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

    def test_illegal_transition_409(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft()
        order_id = created.data["id"]
        bad = self.client.post(
            f"/api/v1/orders/{order_id}/transition/",
            {"fulfilment_status": "shipped"},
            format="json",
        )
        self.assertEqual(bad.status_code, status.HTTP_409_CONFLICT)

    def test_patch_non_draft_409(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft()
        order_id = created.data["id"]
        self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        patched = self.client.patch(
            f"/api/v1/orders/{order_id}/",
            {"delivery_notes": "Nope"},
            format="json",
        )
        self.assertEqual(patched.status_code, status.HTTP_409_CONFLICT)

    def test_transition_blocked_while_payment_pending(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft()
        order_id = created.data["id"]
        self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        blocked = self.client.post(
            f"/api/v1/orders/{order_id}/transition/",
            {"fulfilment_status": "processing"},
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_409_CONFLICT)
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.fulfilment_status, Order.FulfilmentStatus.UNFULFILLED)

    def test_transition_happy_path_after_paid(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft()
        order_id = created.data["id"]
        self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        paid = self.client.post(f"/api/v1/orders/{order_id}/mark-paid/", {}, format="json")
        self.assertEqual(paid.status_code, status.HTTP_200_OK)
        self.assertEqual(paid.data["payment_status"], "paid")
        processing = self.client.post(
            f"/api/v1/orders/{order_id}/transition/",
            {"fulfilment_status": "processing"},
            format="json",
        )
        self.assertEqual(processing.status_code, status.HTTP_200_OK)
        self.assertEqual(processing.data["fulfilment_status"], "processing")

    def test_transition_allow_unpaid_override(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft()
        order_id = created.data["id"]
        self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        processing = self.client.post(
            f"/api/v1/orders/{order_id}/transition/",
            {"fulfilment_status": "processing", "allow_unpaid": True},
            format="json",
        )
        self.assertEqual(processing.status_code, status.HTTP_200_OK)
        self.assertEqual(processing.data["fulfilment_status"], "processing")
        self.assertEqual(processing.data["payment_status"], "pending")

    def test_double_cancel_restores_stock_once(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft(quantity=2)
        order_id = created.data["id"]
        number = created.data["number"]
        self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        first = self.client.post(f"/api/v1/orders/{order_id}/cancel/", {}, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        restores = InventoryAdjustment.objects.filter(
            product=self.product, reason=f"cancel-restore:{number}"
        ).count()
        self.assertEqual(restores, 1)

        second = self.client.post(f"/api/v1/orders/{order_id}/cancel/", {}, format="json")
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(
            InventoryAdjustment.objects.filter(
                product=self.product, reason=f"cancel-restore:{number}"
            ).count(),
            1,
        )

    def test_abandon_payment_keeps_order_unfulfilled(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft()
        order_id = created.data["id"]
        self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        abandoned = self.client.post(
            f"/api/v1/orders/{order_id}/abandon-payment/", {}, format="json"
        )
        self.assertEqual(abandoned.status_code, status.HTTP_200_OK)
        self.assertEqual(abandoned.data["fulfilment_status"], "unfulfilled")
        self.assertEqual(abandoned.data["payment_status"], "cancelled")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

    def test_product_order_usage(self):
        self.client.force_authenticate(self.user)
        created = self._create_draft(quantity=2)
        order_id = created.data["id"]
        self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        usage = self.client.get(f"/api/v1/products/{self.product.id}/order-usage/")
        self.assertEqual(usage.status_code, status.HTTP_200_OK)
        self.assertEqual(len(usage.data), 1)
        self.assertEqual(usage.data[0]["quantity"], 2)
        self.assertEqual(usage.data[0]["order_id"], order_id)


@override_settings(**TEST_SETTINGS)
class OrderFlowPathTests(APITestCase):
    """Exhaustive happy + failure paths for fulfilment/payment/stock."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="flow@example.com", password=PASSWORD, first_name="F"
        )
        self.other = User.objects.create_user(
            email="flow-other@example.com", password=PASSWORD, first_name="O"
        )
        self.store = create_store_for_user(
            user=self.user,
            name="Flow Store",
            currency="USD",
            timezone="UTC",
            business_type="social",
        )
        self.other_store = create_store_for_user(
            user=self.other,
            name="Other Flow Store",
            currency="USD",
            timezone="UTC",
            business_type="social",
        )
        self.customer = Customer.objects.create(store=self.store, name="Buyer")
        self.product = Product.objects.create(
            store=self.store,
            name="Item",
            sku="ITEM-1",
            price=Decimal("10.00"),
            currency="USD",
            stock_quantity=20,
        )
        self.client.force_authenticate(self.user)

    def _draft(self, quantity=1):
        response = self.client.post(
            "/api/v1/orders/",
            {
                "customer_id": self.customer.id,
                "lines": [{"product_id": self.product.id, "quantity": quantity}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data

    def _confirm(self, order_id):
        response = self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def _mark_paid(self, order_id):
        response = self.client.post(f"/api/v1/orders/{order_id}/mark-paid/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def _transition(self, order_id, fulfilment_status, *, allow_unpaid=False, expect=200):
        body = {"fulfilment_status": fulfilment_status}
        if allow_unpaid:
            body["allow_unpaid"] = True
        response = self.client.post(
            f"/api/v1/orders/{order_id}/transition/", body, format="json"
        )
        self.assertEqual(response.status_code, expect)
        return response

    # --- Happy paths ---

    def test_full_paid_lifecycle_to_completed(self):
        draft = self._draft(quantity=2)
        order_id = draft["id"]
        self.assertEqual(self.product.stock_quantity, 20)

        confirmed = self._confirm(order_id)
        self.assertEqual(confirmed["fulfilment_status"], "unfulfilled")
        self.assertEqual(confirmed["payment_status"], "pending")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 18)

        paid = self._mark_paid(order_id)
        self.assertEqual(paid["payment_status"], "paid")
        self.assertEqual(paid["fulfilment_status"], "unfulfilled")

        processing = self._transition(order_id, "processing")
        self.assertEqual(processing.data["fulfilment_status"], "processing")

        shipped = self._transition(order_id, "shipped")
        self.assertEqual(shipped.data["fulfilment_status"], "shipped")

        completed = self._transition(order_id, "completed")
        self.assertEqual(completed.data["fulfilment_status"], "completed")
        self.assertEqual(completed.data["payment_status"], "paid")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 18)

        cancel = self.client.post(f"/api/v1/orders/{order_id}/cancel/", {}, format="json")
        self.assertEqual(cancel.status_code, status.HTTP_409_CONFLICT)

    def test_cancel_draft_does_not_touch_stock(self):
        draft = self._draft(quantity=3)
        cancelled = self.client.post(
            f"/api/v1/orders/{draft['id']}/cancel/", {}, format="json"
        )
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK)
        self.assertEqual(cancelled.data["fulfilment_status"], "cancelled")
        self.assertEqual(cancelled.data["payment_status"], "cancelled")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 20)
        self.assertEqual(
            InventoryAdjustment.objects.filter(product=self.product).count(), 0
        )

    def test_cancel_after_paid_processing_restores_stock_keeps_paid(self):
        draft = self._draft(quantity=2)
        order_id = draft["id"]
        self._confirm(order_id)
        self._mark_paid(order_id)
        self._transition(order_id, "processing")
        cancelled = self.client.post(f"/api/v1/orders/{order_id}/cancel/", {}, format="json")
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK)
        self.assertEqual(cancelled.data["fulfilment_status"], "cancelled")
        self.assertEqual(cancelled.data["payment_status"], "paid")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 20)

    def test_abandon_then_mark_paid_then_process(self):
        draft = self._draft()
        order_id = draft["id"]
        self._confirm(order_id)
        abandoned = self.client.post(
            f"/api/v1/orders/{order_id}/abandon-payment/", {}, format="json"
        )
        self.assertEqual(abandoned.status_code, status.HTTP_200_OK)
        self.assertEqual(abandoned.data["payment_status"], "cancelled")
        self.assertEqual(abandoned.data["fulfilment_status"], "unfulfilled")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 19)

        self._mark_paid(order_id)
        processing = self._transition(order_id, "processing")
        self.assertEqual(processing.data["fulfilment_status"], "processing")
        self.assertEqual(processing.data["payment_status"], "paid")

    def test_abandon_then_cancel_order_restores_stock(self):
        draft = self._draft(quantity=2)
        order_id = draft["id"]
        self._confirm(order_id)
        self.client.post(f"/api/v1/orders/{order_id}/abandon-payment/", {}, format="json")
        cancelled = self.client.post(f"/api/v1/orders/{order_id}/cancel/", {}, format="json")
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK)
        self.assertEqual(cancelled.data["fulfilment_status"], "cancelled")
        self.assertEqual(cancelled.data["payment_status"], "cancelled")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 20)

    def test_allow_unpaid_cod_path_to_shipped(self):
        draft = self._draft()
        order_id = draft["id"]
        self._confirm(order_id)
        self._transition(order_id, "processing", allow_unpaid=True)
        shipped = self._transition(order_id, "shipped", allow_unpaid=True)
        self.assertEqual(shipped.data["fulfilment_status"], "shipped")
        self.assertEqual(shipped.data["payment_status"], "pending")

    def test_patch_draft_updates_lines(self):
        draft = self._draft(quantity=1)
        order_id = draft["id"]
        patched = self.client.patch(
            f"/api/v1/orders/{order_id}/",
            {
                "delivery_notes": "Updated notes",
                "lines": [{"product_id": self.product.id, "quantity": 4}],
            },
            format="json",
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertEqual(patched.data["delivery_notes"], "Updated notes")
        self.assertEqual(patched.data["lines"][0]["quantity"], 4)
        self.assertEqual(patched.data["total"], "40.00")

    # --- Failure paths ---

    def test_double_confirm_rejected(self):
        draft = self._draft()
        order_id = draft["id"]
        self._confirm(order_id)
        second = self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 19)

    def test_skip_fulfilment_step_rejected(self):
        draft = self._draft()
        order_id = draft["id"]
        self._confirm(order_id)
        self._mark_paid(order_id)
        self._transition(order_id, "processing")
        skipped = self._transition(order_id, "completed", expect=status.HTTP_409_CONFLICT)
        self.assertIn("detail", skipped.data)

    def test_ship_while_unfulfilled_rejected(self):
        draft = self._draft()
        order_id = draft["id"]
        self._confirm(order_id)
        self._mark_paid(order_id)
        self._transition(order_id, "shipped", expect=status.HTTP_409_CONFLICT)

    def test_abandon_payment_not_pending_rejected(self):
        draft = self._draft()
        order_id = draft["id"]
        self._confirm(order_id)
        self._mark_paid(order_id)
        bad = self.client.post(
            f"/api/v1/orders/{order_id}/abandon-payment/", {}, format="json"
        )
        self.assertEqual(bad.status_code, status.HTTP_409_CONFLICT)

    def test_abandon_payment_after_processing_rejected(self):
        draft = self._draft()
        order_id = draft["id"]
        self._confirm(order_id)
        self._transition(order_id, "processing", allow_unpaid=True)
        bad = self.client.post(
            f"/api/v1/orders/{order_id}/abandon-payment/", {}, format="json"
        )
        self.assertEqual(bad.status_code, status.HTTP_409_CONFLICT)

    def test_mark_paid_on_cancelled_rejected(self):
        draft = self._draft()
        order_id = draft["id"]
        self._confirm(order_id)
        self.client.post(f"/api/v1/orders/{order_id}/cancel/", {}, format="json")
        bad = self.client.post(f"/api/v1/orders/{order_id}/mark-paid/", {}, format="json")
        self.assertEqual(bad.status_code, status.HTTP_409_CONFLICT)

    def test_mark_paid_idempotent(self):
        draft = self._draft()
        order_id = draft["id"]
        self._confirm(order_id)
        self._mark_paid(order_id)
        again = self.client.post(f"/api/v1/orders/{order_id}/mark-paid/", {}, format="json")
        self.assertEqual(again.status_code, status.HTTP_200_OK)
        self.assertEqual(again.data["payment_status"], "paid")

    def test_confirm_inactive_product_rejected(self):
        draft = self._draft()
        order_id = draft["id"]
        self.product.is_active = False
        self.product.save(update_fields=["is_active", "updated_at"])
        bad = self.client.post(f"/api/v1/orders/{order_id}/confirm/", {}, format="json")
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 20)
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.fulfilment_status, Order.FulfilmentStatus.DRAFT)

    def test_ship_blocked_when_payment_still_pending_even_after_processing_cod(self):
        """After COD processing, shipping still needs allow_unpaid or paid."""
        draft = self._draft()
        order_id = draft["id"]
        self._confirm(order_id)
        self._transition(order_id, "processing", allow_unpaid=True)
        blocked = self._transition(order_id, "shipped", expect=status.HTTP_409_CONFLICT)
        self.assertIn("Payment must be paid", blocked.data["detail"])
        self._transition(order_id, "shipped", allow_unpaid=True)

    def test_no_store_returns_404(self):
        lonely = User.objects.create_user(
            email="lonely@example.com", password=PASSWORD, first_name="L"
        )
        self.client.force_authenticate(lonely)
        response = self.client.get("/api/v1/orders/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_rejects_foreign_customer(self):
        foreign_customer = Customer.objects.create(
            store=self.other_store, name="Foreign", email="f@example.com"
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/orders/",
            {
                "customer_id": foreign_customer.id,
                "lines": [{"product_id": self.product.id, "quantity": 1}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_foreign_product(self):
        foreign_product = Product.objects.create(
            store=self.other_store,
            name="Other Hoodie",
            sku="OTHER-HOOD",
            price=Decimal("10.00"),
            currency="USD",
            stock_quantity=5,
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/orders/",
            {
                "customer_id": self.customer.id,
                "lines": [{"product_id": foreign_product.id, "quantity": 1}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_filters_and_ordering(self):
        draft = self._draft()
        confirmed = self._draft(quantity=1)
        self._confirm(confirmed["id"])

        drafts = self.client.get("/api/v1/orders/", {"fulfilment_status": "draft"})
        draft_results = drafts.data["results"]
        self.assertEqual(len(draft_results), 1)
        self.assertEqual(draft_results[0]["id"], draft["id"])

        pending = self.client.get("/api/v1/orders/", {"payment_status": "pending"})
        self.assertEqual(len(pending.data["results"]), 1)
        self.assertEqual(pending.data["results"][0]["id"], confirmed["id"])

        ordered = self.client.get("/api/v1/orders/", {"ordering": "number"})
        numbers = [row["number"] for row in ordered.data["results"]]
        self.assertEqual(numbers, sorted(numbers))

        bilal = Customer.objects.create(
            store=self.store, name="Bilal", email="b@example.com"
        )
        self.client.post(
            "/api/v1/orders/",
            {
                "customer_id": bilal.id,
                "lines": [{"product_id": self.product.id, "quantity": 1}],
            },
            format="json",
        )
        by_customer = self.client.get(
            "/api/v1/orders/", {"ordering": "customer__name"}
        )
        names = [row["customer_name"] for row in by_customer.data["results"]]
        self.assertEqual(names, sorted(names))
        by_customer_desc = self.client.get(
            "/api/v1/orders/", {"ordering": "-customer__name"}
        )
        names_desc = [
            row["customer_name"] for row in by_customer_desc.data["results"]
        ]
        self.assertEqual(names_desc, sorted(names, reverse=True))

    def test_list_query_count_is_bounded(self):
        for _ in range(3):
            self._draft(quantity=1)
        # store resolve + count + list page (select_related customer); no N+1 on lines.
        with self.assertNumQueries(3):
            response = self.client.get("/api/v1/orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 3)

    def test_lock_products_orders_by_pk(self):
        from django.db import transaction

        from apps.orders.services import _lock_products

        second = Product.objects.create(
            store=self.store,
            name="Belt",
            sku="BELT-1",
            price=Decimal("10.00"),
            currency="USD",
            stock_quantity=5,
        )
        # Reverse insertion order should still lock ascending by pk.
        with transaction.atomic():
            locked = _lock_products(
                store=self.store,
                product_ids=[second.id, self.product.id],
            )
        self.assertEqual(list(locked.keys()), sorted([self.product.id, second.id]))
