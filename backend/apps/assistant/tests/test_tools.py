from decimal import Decimal
from unittest.mock import patch

from apps.assistant import tools
from apps.assistant.tests.base import AssistantTestCase
from apps.orders import services as orders_services
from apps.orders.models import Order, OrderEvent
from apps.payments.models import PaymentCheckout, PaymentInvoice
from apps.products.models import Product


class ReadOnlyToolsTests(AssistantTestCase):
    def test_list_unpaid_orders_scopes_to_store(self):
        order_id = self.confirmed_order()
        other_customer = self.client.post  # noqa: F841 — keep lints quiet, unused placeholder

        output, side_effect = tools._tool_list_unpaid_orders(
            store=self.store, user=self.user, conversation=None, min_days_unpaid=0
        )
        numbers = [row["order_number"] for row in output["orders"]]
        self.assertIn(Order.objects.get(pk=order_id).number, numbers)
        self.assertIsNone(side_effect)

        # Another store's unpaid order must never leak into this store's list.
        from apps.customers.models import Customer
        from apps.orders.services import create_draft

        other_customer_obj = Customer.objects.create(store=self.other_store, name="Z")
        other_product = Product.objects.create(
            store=self.other_store, name="X", sku="X-1", price="9.00", currency="USD", stock_quantity=5
        )
        create_draft(
            store=self.other_store,
            user=self.other,
            customer=other_customer_obj,
            lines=[{"product_id": other_product.id, "quantity": 1}],
        )
        output2, _ = tools._tool_list_unpaid_orders(
            store=self.store, user=self.user, conversation=None, min_days_unpaid=0
        )
        self.assertEqual(len(output2["orders"]), len(output["orders"]))

    def test_list_unpaid_orders_payment_status_filter_narrows_to_exactly_one_status(self):
        from apps.orders.services import create_draft

        draft_id = create_draft(
            store=self.store, user=self.user, customer=self.customer,
            lines=[{"product_id": self.product.id, "quantity": 1}],
        ).id  # payment_status: unpaid
        confirmed_id = self.confirmed_order()  # confirm_order sets payment_status: pending

        unpaid_only, _ = tools._tool_list_unpaid_orders(
            store=self.store, user=self.user, conversation=None, payment_status="unpaid"
        )
        self.assertEqual(unpaid_only["payment_status_filter"], "unpaid")
        unpaid_ids = {o["order_id"] for o in unpaid_only["orders"]}
        self.assertIn(draft_id, unpaid_ids)
        self.assertNotIn(confirmed_id, unpaid_ids)

        pending_only, _ = tools._tool_list_unpaid_orders(
            store=self.store, user=self.user, conversation=None, payment_status="pending"
        )
        self.assertEqual(pending_only["payment_status_filter"], "pending")
        pending_ids = {o["order_id"] for o in pending_only["orders"]}
        self.assertIn(confirmed_id, pending_ids)
        self.assertNotIn(draft_id, pending_ids)

        both, _ = tools._tool_list_unpaid_orders(store=self.store, user=self.user, conversation=None)
        self.assertEqual(both["payment_status_filter"], "unpaid_and_pending")
        both_ids = {o["order_id"] for o in both["orders"]}
        self.assertEqual(both_ids, unpaid_ids | pending_ids)

    def test_list_unpaid_orders_ignores_a_garbage_payment_status_value(self):
        # strict mode's enum constrains what the model CAN send, but the dispatch function
        # shouldn't trust that alone — a stray/invalid value must fall back to "both", not crash
        # or silently return nothing.
        self.confirmed_order()
        output, _ = tools._tool_list_unpaid_orders(
            store=self.store, user=self.user, conversation=None, payment_status="paid"
        )
        self.assertEqual(output["payment_status_filter"], "unpaid_and_pending")

    def test_order_status_summary_groups_correctly_not_one_row_per_order(self):
        self.confirmed_order()
        self.confirmed_order()
        output, side_effect = tools._tool_order_status_summary(
            store=self.store, user=self.user, conversation=None
        )
        self.assertIsNone(side_effect)
        self.assertEqual(output["total_orders"], 2)
        self.assertEqual(output["by_fulfilment_status"]["unfulfilled"], 2)
        self.assertEqual(output["by_payment_status"]["pending"], 2)

    def test_list_low_stock_products_only_returns_low_stock(self):
        output, _ = tools._tool_list_low_stock_products(store=self.store, user=self.user, conversation=None)
        skus = [row["sku"] for row in output["products"]]
        self.assertIn(self.low_stock_product.sku, skus)
        self.assertNotIn(self.product.sku, skus)

    def test_get_order_includes_source_message_and_notes(self):
        self.confirmed_order()
        order = Order.objects.get(store=self.store)
        order.source_message = "2 hoodies please"
        order.internal_notes = "fragile, pack well"
        order.save(update_fields=["source_message", "internal_notes"])

        output, _ = tools._tool_get_order(store=self.store, user=self.user, conversation=None, order_number=order.number)
        self.assertEqual(output["source_message"], "2 hoodies please")
        self.assertEqual(output["internal_notes"], "fragile, pack well")

    def test_list_customer_orders_is_scoped_to_one_customer_not_name_filtered_from_store_lists(self):
        from apps.customers.models import Customer
        from apps.orders.services import create_draft

        # Two customers sharing a first name in the same store — the real bug: a store-wide
        # list filtered by name would have silently merged their orders.
        namesake = Customer.objects.create(store=self.store, name="Ayesha Khan", email="other@x.com")
        mine_id = self.confirmed_order()  # self.customer == "Ayesha Khan"
        create_draft(
            store=self.store, user=self.user, customer=namesake,
            lines=[{"product_id": self.product.id, "quantity": 1}],
        )

        output, side_effect = tools._tool_list_customer_orders(
            store=self.store, user=self.user, conversation=None, customer_id=self.customer.id
        )
        self.assertIsNone(side_effect)
        self.assertEqual(output["customer"]["id"], self.customer.id)
        self.assertEqual(output["total_orders"], 1)
        self.assertEqual(output["orders"][0]["order_number"], Order.objects.get(pk=mine_id).number)
        self.assertFalse(output["truncated"])

    def test_list_customer_orders_reports_open_payment_request(self):
        order_id = self.confirmed_order()
        order = Order.objects.get(pk=order_id)
        PaymentCheckout.objects.create(
            order=order, paypal_order_id="PP-1", status=PaymentCheckout.Status.APPROVED,
            approve_url="https://sandbox.paypal.com/pay-now",
            amount=order.total, currency=order.currency,
        )
        output, _ = tools._tool_list_customer_orders(
            store=self.store, user=self.user, conversation=None, customer_id=self.customer.id
        )
        self.assertEqual(output["orders"][0]["open_payment_request"], "pay_now_link_open")
        self.assertEqual(output["by_payment_status"]["pending"], 1)

    def test_list_customer_orders_multiple_name_matches_asks_instead_of_guessing(self):
        from apps.customers.models import Customer

        Customer.objects.create(store=self.store, name="Bilal Ahmed", email="a@x.com")
        Customer.objects.create(store=self.store, name="Bilal Ahmed", email="b@x.com")
        output, side_effect = tools._tool_list_customer_orders(
            store=self.store, user=self.user, conversation=None, customer="Bilal Ahmed"
        )
        self.assertIsNone(side_effect)
        self.assertEqual(len(output["multiple_matches"]), 2)
        self.assertNotIn("orders", output)

    def test_list_customer_orders_no_match_reports_error_not_empty_list(self):
        output, _ = tools._tool_list_customer_orders(
            store=self.store, user=self.user, conversation=None, customer="Nobody Here"
        )
        self.assertIn("error", output)
        self.assertNotIn("orders", output)

    def test_list_unpaid_and_recent_orders_report_truncation(self):
        from apps.customers.models import Customer
        from apps.orders.services import create_draft

        extra_customer = Customer.objects.create(store=self.store, name="Bulk Buyer")
        for _ in range(tools.STORE_LIST_LIMIT + 2):
            create_draft(
                store=self.store, user=self.user, customer=extra_customer,
                lines=[{"product_id": self.product.id, "quantity": 1}],
            )

        unpaid, _ = tools._tool_list_unpaid_orders(
            store=self.store, user=self.user, conversation=None, min_days_unpaid=0
        )
        self.assertTrue(unpaid["truncated"])
        self.assertEqual(len(unpaid["orders"]), tools.STORE_LIST_LIMIT)
        self.assertIn("note", unpaid)

        recent, _ = tools._tool_list_recent_orders(store=self.store, user=self.user, conversation=None)
        self.assertEqual(recent["total_count"], unpaid["total_count"])
        self.assertTrue(recent["truncated"])

    def test_list_recent_orders_date_range_filters_by_created_at(self):
        in_range_id = self.confirmed_order()
        out_of_range_id = self.confirmed_order()
        Order.objects.filter(pk=in_range_id).update(created_at="2026-11-03T12:00:00Z")
        Order.objects.filter(pk=out_of_range_id).update(created_at="2026-10-01T12:00:00Z")

        output, _ = tools._tool_list_recent_orders(
            store=self.store, user=self.user, conversation=None,
            created_after="2026-11-01", created_before="2026-11-07",
        )
        order_ids = {row["order_id"] for row in output["orders"]}
        self.assertIn(in_range_id, order_ids)
        self.assertNotIn(out_of_range_id, order_ids)

    def test_list_recent_orders_rejects_an_unparsable_date(self):
        output, _ = tools._tool_list_recent_orders(
            store=self.store, user=self.user, conversation=None, created_after="not-a-date"
        )
        self.assertIn("error", output)
        self.assertNotIn("orders", output)

    def test_find_customers_includes_notes(self):
        self.customer.notes = "always wants gift wrap"
        self.customer.save(update_fields=["notes"])
        output, _ = tools._tool_find_customers(store=self.store, user=self.user, conversation=None, query="Ayesha")
        self.assertEqual(output["customers"][0]["notes"], "always wants gift wrap")

    def test_find_products_matches_own_catalog_by_name_or_sku(self):
        output, side_effect = tools._tool_find_products(
            store=self.store, user=self.user, conversation=None, query="hoodie"
        )
        self.assertIsNone(side_effect)
        skus = [row["sku"] for row in output["products"]]
        self.assertIn(self.product.sku, skus)
        self.assertNotIn(self.low_stock_product.sku, skus)

        by_sku, _ = tools._tool_find_products(
            store=self.store, user=self.user, conversation=None, query=self.low_stock_product.sku
        )
        self.assertEqual([row["sku"] for row in by_sku["products"]], [self.low_stock_product.sku])

    def test_find_products_scopes_to_store(self):
        Product.objects.create(
            store=self.other_store, name="Water Bottle", sku="BOTTLE-1", price="9.00", currency="USD",
            stock_quantity=5,
        )
        output, _ = tools._tool_find_products(
            store=self.store, user=self.user, conversation=None, query="water bottle"
        )
        self.assertEqual(output["products"], [])


class AutoExecuteToolsTests(AssistantTestCase):
    def test_create_draft_order_resolves_sku_without_touching_stock(self):
        output, side_effect = tools._tool_create_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            customer={"name": "New Customer", "email": "new@example.com"},
            lines=[{"sku": self.product.sku, "quantity": 2}],
            source_message="2 black hoodies please",
        )
        self.assertNotIn("error", output)
        self.assertEqual(side_effect["kind"], "order_created")

        order = Order.objects.get(pk=side_effect["order_id"])
        self.assertEqual(order.fulfilment_status, Order.FulfilmentStatus.DRAFT)
        self.assertEqual(order.source_message, "2 black hoodies please")
        self.assertEqual(order.customer.email, "new@example.com")

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10, "a Draft order must not deduct stock")

        note = OrderEvent.objects.filter(order=order, origin=OrderEvent.Origin.ASSISTANT).first()
        self.assertIsNotNone(note)

    def test_create_draft_order_resolves_a_line_by_product_name(self):
        # Reproduces the reported incident: a product the seller names by its real name (not
        # an invented sku) must resolve via search, same as adjust_product_stock/update_product.
        bag = Product.objects.create(
            store=self.store, name="Mag Tote Bag", sku="MAG-TOTE-BAG", price="12.00",
            currency="USD", stock_quantity=5,
        )
        output, side_effect = tools._tool_create_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            customer={"name": "New Customer", "email": "new@example.com"},
            lines=[{"product": "tote bag", "quantity": 1}],
        )
        self.assertNotIn("error", output)
        order = Order.objects.get(pk=side_effect["order_id"])
        self.assertEqual(order.lines.get().product_id, bag.id)

    def test_create_draft_order_resolves_a_line_by_sku_too(self):
        output, side_effect = tools._tool_create_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            customer={"name": "New Customer", "email": "new@example.com"},
            lines=[{"product": self.product.sku, "quantity": 1}],
        )
        self.assertNotIn("error", output)
        order = Order.objects.get(pk=side_effect["order_id"])
        self.assertEqual(order.lines.get().product_id, self.product.id)

    def test_create_draft_order_line_ambiguity_and_not_found_create_nothing(self):
        Product.objects.create(
            store=self.store, name="Grey Hoodie", sku="HOOD-GRY-M", price="49.00",
            currency="USD", stock_quantity=4,
        )
        before = Order.objects.filter(store=self.store).count()

        ambiguous, side_effect1 = tools._tool_create_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            customer={"name": "New Customer", "email": "new@example.com"},
            lines=[{"product": "hoodie", "quantity": 1}],
        )
        self.assertIn("multiple_matches", ambiguous)
        self.assertIsNone(side_effect1)

        not_found, side_effect2 = tools._tool_create_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            customer={"name": "New Customer", "email": "new@example.com"},
            lines=[{"product": "totte bag", "quantity": 1}],
        )
        self.assertIn("error", not_found)
        self.assertIsNone(side_effect2)

        self.assertEqual(
            Order.objects.filter(store=self.store).count(), before, "neither case should create an order"
        )

    def test_create_draft_order_reuses_existing_customer_by_email(self):
        output, side_effect = tools._tool_create_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            customer={"name": "Ayesha Khan", "email": self.customer.email},
            lines=[{"sku": self.product.sku, "quantity": 1}],
        )
        self.assertNotIn("error", output)
        order = Order.objects.get(pk=side_effect["order_id"])
        self.assertEqual(order.customer_id, self.customer.id)

    def test_create_draft_order_reuses_existing_customer_by_name_alone(self):
        from apps.customers.models import Customer

        before = Customer.objects.filter(store=self.store).count()
        output, side_effect = tools._tool_create_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            customer={"name": self.customer.name},
            lines=[{"sku": self.product.sku, "quantity": 1}],
        )
        self.assertNotIn("error", output)
        order = Order.objects.get(pk=side_effect["order_id"])
        self.assertEqual(order.customer_id, self.customer.id, "a name-only match must reuse the existing customer")
        self.assertEqual(
            Customer.objects.filter(store=self.store).count(), before, "no duplicate customer should be created"
        )

    def test_create_draft_order_flags_a_near_miss_name_instead_of_creating(self):
        from apps.customers.models import Customer

        self.customer.name = "Orbiz Email Test"
        self.customer.save(update_fields=["name"])
        before = Customer.objects.filter(store=self.store).count()

        output, side_effect = tools._tool_create_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            customer={"name": "Orbiz Test Email"},
            lines=[{"sku": self.product.sku, "quantity": 1}],
        )
        self.assertIsNone(side_effect)
        self.assertIn("possible_match", output)
        self.assertEqual(output["possible_match"]["id"], self.customer.id)
        self.assertEqual(
            Customer.objects.filter(store=self.store).count(), before, "an ambiguous name must not create anyone"
        )

    def test_create_draft_order_flags_multiple_exact_name_matches(self):
        from apps.customers.models import Customer

        Customer.objects.create(store=self.store, name="Bilal Ahmed", email="bilal1@example.com")
        Customer.objects.create(store=self.store, name="Bilal Ahmed", email="bilal2@example.com")
        before = Customer.objects.filter(store=self.store).count()

        output, side_effect = tools._tool_create_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            customer={"name": "Bilal Ahmed"},
            lines=[{"sku": self.product.sku, "quantity": 1}],
        )
        self.assertIsNone(side_effect)
        self.assertIn("multiple_matches", output)
        self.assertEqual(len(output["multiple_matches"]), 2)
        self.assertEqual(
            Customer.objects.filter(store=self.store).count(),
            before,
            "an exact name shared by two customers must not silently pick one or create a third",
        )

    def test_create_draft_order_confirmed_new_skips_the_near_miss_check(self):
        from apps.customers.models import Customer

        self.customer.name = "Orbiz Email Test"
        self.customer.save(update_fields=["name"])
        before = Customer.objects.filter(store=self.store).count()

        output, side_effect = tools._tool_create_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            customer={"name": "Orbiz Test Email", "confirmed_new": True},
            lines=[{"sku": self.product.sku, "quantity": 1}],
        )
        self.assertNotIn("error", output)
        self.assertNotIn("possible_match", output)
        order = Order.objects.get(pk=side_effect["order_id"])
        self.assertNotEqual(order.customer_id, self.customer.id)
        self.assertEqual(Customer.objects.filter(store=self.store).count(), before + 1)

    def test_add_customer_reuses_existing_customer_by_name_alone(self):
        from apps.customers.models import Customer

        before = Customer.objects.filter(store=self.store).count()
        output, _ = tools._tool_add_customer(
            store=self.store, user=self.user, conversation=None, name=self.customer.name
        )
        self.assertEqual(output["customer_id"], self.customer.id)
        self.assertEqual(Customer.objects.filter(store=self.store).count(), before)

    def test_add_customer_dedupes_by_email(self):
        output, _ = tools._tool_add_customer(
            store=self.store, user=self.user, conversation=None, name="Ayesha", email=self.customer.email
        )
        self.assertEqual(output["customer_id"], self.customer.id)

    def test_update_customer_notes(self):
        output, _ = tools._tool_update_customer_notes(
            store=self.store, user=self.user, conversation=None, customer_id=self.customer.id, notes="prefers Roman Urdu"
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.notes, "prefers Roman Urdu")
        self.assertEqual(output["notes"], "prefers Roman Urdu")

    @patch("apps.payments.services.paypal_client.create_order")
    def test_create_checkout_auto_executes_and_notes_origin(self, mock_create):
        mock_create.return_value = {
            "id": "PAYPAL-ORDER-1",
            "status": "CREATED",
            "approve_url": "https://sandbox.paypal.com/x",
            "raw": {},
        }
        order_id = self.confirmed_order()
        output, side_effect = tools._tool_create_checkout(
            store=self.store, user=self.user, conversation=None, order_id=order_id
        )
        self.assertNotIn("error", output)
        self.assertIsNone(side_effect, "touching an existing order must not re-trigger a draft-order card")
        note = OrderEvent.objects.filter(
            order_id=order_id, origin=OrderEvent.Origin.ASSISTANT, message__icontains="checkout"
        ).first()
        self.assertIsNotNone(note)

    def test_create_checkout_surfaces_application_error_conversationally(self):
        # No PayPal credentials configured in this sub-test → ServiceUnavailableError, not a 500.
        order_id = self.confirmed_order()
        with patch("apps.payments.services.paypal_client.create_order", side_effect=RuntimeError("boom")):
            output, side_effect = tools.dispatch(
                "create_checkout",
                store=self.store,
                user=self.user,
                conversation=None,
                arguments={"order_id": order_id},
            )
        self.assertIn("error", output)


class OrderAutomationToolsTests(AssistantTestCase):
    def _draft_order_id(self) -> int:
        created = self.client.post(
            "/api/v1/orders/",
            {"customer_id": self.customer.id, "lines": [{"product_id": self.product.id, "quantity": 1}]},
            format="json",
        )
        assert created.status_code == 201, created.data
        return created.data["id"]

    def test_update_draft_order_changes_lines_and_notes(self):
        order_id = self._draft_order_id()
        output, side_effect = tools._tool_update_draft_order(
            store=self.store,
            user=self.user,
            conversation=None,
            order_id=order_id,
            lines=[{"sku": self.product.sku, "quantity": 3}],
            delivery_notes="leave at the gate",
        )
        self.assertNotIn("error", output)
        self.assertIsNone(side_effect, "editing an existing draft must not re-trigger its card")
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.delivery_notes, "leave at the gate")
        self.assertEqual(order.lines.get().quantity, 3)

    def test_update_draft_order_rejects_a_confirmed_order(self):
        order_id = self.confirmed_order()
        output, _ = tools._tool_update_draft_order(
            store=self.store, user=self.user, conversation=None, order_id=order_id, delivery_notes="x"
        )
        self.assertIn("error", output)

    def test_cancel_order_restores_deducted_stock(self):
        order_id = self.confirmed_order()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 9)

        output, side_effect = tools._tool_cancel_order(
            store=self.store, user=self.user, conversation=None, order_id=order_id
        )
        self.assertNotIn("error", output)
        self.assertIsNone(side_effect)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10, "cancelling must restore deducted stock")

        output2, _ = tools._tool_cancel_order(
            store=self.store, user=self.user, conversation=None, order_id=order_id
        )
        self.assertIn("error", output2)

    def test_mark_order_paid_happy_path_and_cancelled_conflict(self):
        order_id = self.confirmed_order()
        output, side_effect = tools._tool_mark_order_paid(
            store=self.store, user=self.user, conversation=None, order_id=order_id
        )
        self.assertNotIn("error", output)
        self.assertIsNone(side_effect)
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)

        cancelled_order_id = self.confirmed_order()
        order = Order.objects.get(pk=cancelled_order_id)
        orders_services.cancel_order(order=order, user=self.user)
        output2, _ = tools._tool_mark_order_paid(
            store=self.store, user=self.user, conversation=None, order_id=cancelled_order_id
        )
        self.assertIn("error", output2)

    def test_transition_order_status_requires_payment_unless_allowed(self):
        order_id = self.confirmed_order()
        blocked, _ = tools._tool_transition_order_status(
            store=self.store,
            user=self.user,
            conversation=None,
            order_id=order_id,
            fulfilment_status="processing",
        )
        self.assertIn("error", blocked)

        allowed, side_effect = tools._tool_transition_order_status(
            store=self.store,
            user=self.user,
            conversation=None,
            order_id=order_id,
            fulfilment_status="processing",
            allow_unpaid=True,
        )
        self.assertNotIn("error", allowed)
        self.assertIsNone(side_effect)
        self.assertEqual(
            Order.objects.get(pk=order_id).fulfilment_status, Order.FulfilmentStatus.PROCESSING
        )

    def test_abandon_order_payment_happy_path_and_wrong_state_conflict(self):
        order_id = self.confirmed_order()
        output, side_effect = tools._tool_abandon_order_payment(
            store=self.store, user=self.user, conversation=None, order_id=order_id
        )
        self.assertNotIn("error", output)
        self.assertIsNone(side_effect)
        self.assertEqual(
            Order.objects.get(pk=order_id).payment_status, Order.PaymentStatus.CANCELLED
        )

        draft_order_id = self._draft_order_id()
        output2, _ = tools._tool_abandon_order_payment(
            store=self.store, user=self.user, conversation=None, order_id=draft_order_id
        )
        self.assertIn("error", output2)

    @patch("apps.payments.services.paypal_client.create_order")
    def test_email_payment_link_creates_the_link_when_none_is_open_and_emails_it(self, mock_create):
        from apps.notifications.models import EmailLog

        mock_create.return_value = {
            "id": "PAYPAL-ORDER-9",
            "status": "CREATED",
            "approve_url": "https://sandbox.paypal.com/pay-now",
            "raw": {},
        }
        order_id = self.confirmed_order()
        output, side_effect = tools._tool_email_payment_link(
            store=self.store,
            user=self.user,
            conversation=None,
            order_id=order_id,
            recipient_email="buyer@example.com",
        )
        self.assertNotIn("error", output)
        self.assertIsNone(side_effect)
        self.assertEqual(output["emailed_to"], "buyer@example.com")
        self.assertEqual(output["link_type"], "checkout", "the pay-now link, not an invoice")
        self.assertFalse(PaymentInvoice.objects.filter(order_id=order_id).exists())
        self.assertTrue(EmailLog.objects.filter(recipient="buyer@example.com").exists())

    def test_email_payment_link_refuses_a_draft(self):
        output, _ = tools._tool_email_payment_link(
            store=self.store, user=self.user, conversation=None, order_id=self._draft_order_id()
        )
        self.assertIn("error", output)

    def test_cancel_invoice_happy_path_and_nothing_open_conflict(self):
        order_id = self.confirmed_order()
        order = Order.objects.get(pk=order_id)
        PaymentInvoice.objects.create(
            order=order,
            invoice_number="INV-TEST-1",
            status=PaymentInvoice.Status.DRAFT,
            amount=order.total,
            currency=order.currency,
        )
        output, side_effect = tools._tool_cancel_invoice(
            store=self.store, user=self.user, conversation=None, order_id=order_id
        )
        self.assertNotIn("error", output)
        self.assertIsNone(side_effect)
        invoice = PaymentInvoice.objects.get(order=order)
        self.assertEqual(invoice.status, PaymentInvoice.Status.CANCELLED)
        note = OrderEvent.objects.filter(
            order=order, origin=OrderEvent.Origin.ASSISTANT, message__icontains="Invoice cancelled"
        ).first()
        self.assertIsNotNone(note)

        output2, _ = tools._tool_cancel_invoice(
            store=self.store, user=self.user, conversation=None, order_id=order_id
        )
        self.assertIn("error", output2)


class ProductAutomationToolsTests(AssistantTestCase):
    def _adjust(self, **kwargs):
        return tools._tool_adjust_product_stock(
            store=self.store, user=self.user, conversation=None, **kwargs
        )

    def test_adjust_product_stock_by_name_and_rejects_going_negative(self):
        output, side_effect = self._adjust(product="Black Hoodie", delta=5, reason="restock")
        self.assertIsNone(side_effect)
        self.assertEqual(output["stock_quantity_before"], 10)
        self.assertEqual(output["stock_quantity_after"], 15)

        output2, _ = self._adjust(product="Black Hoodie", delta=-999, reason="too many")
        self.assertIn("error", output2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 15, "a rejected adjustment must not change stock")

    def test_adjust_product_stock_by_sku_is_case_insensitive(self):
        output, _ = self._adjust(product="hood-blk-m", delta=1, reason="restock")
        self.assertEqual(output["sku"], self.product.sku)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 11)

    def test_adjust_product_stock_restocks_the_product_named_not_a_remembered_id(self):
        # The reported incident: restocking "Water Bottle 750ml" kept landing on the hoodie
        # because the model passed a stale product_id. Ids are no longer accepted at all — a
        # leftover one is ignored and the named product is the one that changes.
        bottle = Product.objects.create(
            store=self.store, name="Water Bottle 750ml", sku="BTL-750", price="9.00",
            currency="USD", stock_quantity=7,
        )
        output, _ = self._adjust(
            product="Water Bottle 750ml", product_id=self.product.id, delta=3, reason="restock"
        )
        self.assertEqual(output["sku"], "BTL-750")
        bottle.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(bottle.stock_quantity, 10)
        self.assertEqual(self.product.stock_quantity, 10, "the hoodie must not be touched")

    def test_adjust_product_stock_asks_when_the_name_is_ambiguous(self):
        Product.objects.create(
            store=self.store, name="Grey Hoodie", sku="HOOD-GRY-M", price="49.00",
            currency="USD", stock_quantity=4,
        )
        output, _ = self._adjust(product="hoodie", delta=3, reason="restock")
        self.assertEqual(len(output["multiple_matches"]), 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10, "an ambiguous name must not change anything")

    def test_adjust_product_stock_refuses_unknown_or_missing_product(self):
        unknown, _ = self._adjust(product="Water Bottle", delta=3, reason="restock")
        missing, _ = self._adjust(delta=3, reason="restock")
        self.assertIn("error", unknown)
        self.assertIn("error", missing)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

    def test_create_product_happy_path_and_duplicate_sku_conflict(self):
        output, side_effect = tools._tool_create_product(
            store=self.store,
            user=self.user,
            conversation=None,
            name="Water Bottle",
            sku="bottle-1",
            price="9.99",
            stock_quantity=20,
        )
        self.assertIsNone(side_effect)
        self.assertNotIn("error", output)
        product = Product.objects.get(pk=output["product_id"])
        self.assertEqual(product.sku, "BOTTLE-1")
        self.assertEqual(product.stock_quantity, 20)

        output2, _ = tools._tool_create_product(
            store=self.store,
            user=self.user,
            conversation=None,
            name="Duplicate",
            sku=self.product.sku,
            price="5.00",
        )
        self.assertIn("error", output2)

    def test_update_product_by_name_changes_price(self):
        output, side_effect = tools._tool_update_product(
            store=self.store, user=self.user, conversation=None, product="Black Hoodie", price="55.00"
        )
        self.assertIsNone(side_effect)
        self.assertEqual(output["price"], "55.00")
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("55.00"))

    def test_update_product_refuses_unknown_product_and_ignores_a_stale_id(self):
        output, _ = tools._tool_update_product(
            store=self.store,
            user=self.user,
            conversation=None,
            product="Water Bottle 750ml",
            product_id=self.product.id,
            price="999.00",
        )
        self.assertIn("error", output)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("49.00"), "a stale id must never pick the target")


class PaginationTests(AssistantTestCase):
    """
    The same offset/total_count/truncated/next_offset pattern, applied uniformly across every
    list/search tool — orders, customers, and products alike. Each test shrinks the relevant page
    size via patch() to 2, so a handful of rows is enough to exercise "page 1 truncated, page 2
    (reached via the previous page's own next_offset) is the real remainder, no overlap, no
    offset ever invented by the caller".
    """

    def _extra_orders(self, n: int) -> None:
        from apps.orders.services import create_draft

        for _ in range(n):
            create_draft(
                store=self.store,
                user=self.user,
                customer=self.customer,
                lines=[{"product_id": self.product.id, "quantity": 1}],
            )

    def test_list_unpaid_orders_pages_through_every_order_exactly_once(self):
        self._extra_orders(5)  # + the 2 fixture products' draft orders below = enough for 2 pages
        with patch.object(tools, "STORE_LIST_LIMIT", 2):
            page1, _ = tools._tool_list_unpaid_orders(store=self.store, user=self.user, conversation=None)
            self.assertEqual(page1["total_count"], 5)
            self.assertTrue(page1["truncated"])
            self.assertEqual(len(page1["orders"]), 2)
            self.assertEqual(page1["next_offset"], 2)

            page2, _ = tools._tool_list_unpaid_orders(
                store=self.store, user=self.user, conversation=None, offset=page1["next_offset"]
            )
            self.assertEqual(len(page2["orders"]), 2)
            self.assertTrue(page2["truncated"])
            page1_ids = {o["order_id"] for o in page1["orders"]}
            page2_ids = {o["order_id"] for o in page2["orders"]}
            self.assertEqual(page1_ids & page2_ids, set(), "pages must never overlap")

            page3, _ = tools._tool_list_unpaid_orders(
                store=self.store, user=self.user, conversation=None, offset=page2["next_offset"]
            )
            self.assertEqual(len(page3["orders"]), 1)
            self.assertFalse(page3["truncated"])
            self.assertNotIn("next_offset", page3)

    def test_list_recent_orders_pagination(self):
        self._extra_orders(5)
        with patch.object(tools, "STORE_LIST_LIMIT", 2):
            page1, _ = tools._tool_list_recent_orders(store=self.store, user=self.user, conversation=None, limit=2)
            self.assertTrue(page1["truncated"])
            page2, _ = tools._tool_list_recent_orders(
                store=self.store, user=self.user, conversation=None, limit=2, offset=page1["next_offset"]
            )
            self.assertEqual(
                {o["order_id"] for o in page1["orders"]} & {o["order_id"] for o in page2["orders"]}, set()
            )

    def test_list_low_stock_products_pagination(self):
        for i in range(3):
            Product.objects.create(
                store=self.store, name=f"Low {i}", sku=f"LOW-{i}", price=Decimal("5.00"),
                currency="USD", stock_quantity=1, low_stock_threshold=5,
            )
        with patch.object(tools, "STORE_LIST_LIMIT", 2):
            # self.low_stock_product + the 3 new ones = 4 total.
            page1, _ = tools._tool_list_low_stock_products(store=self.store, user=self.user, conversation=None)
            self.assertEqual(page1["total_count"], 4)
            self.assertTrue(page1["truncated"])
            page2, _ = tools._tool_list_low_stock_products(
                store=self.store, user=self.user, conversation=None, offset=page1["next_offset"]
            )
            self.assertEqual(len(page1["products"]) + len(page2["products"]), 4)
            page1_skus = {p["sku"] for p in page1["products"]}
            page2_skus = {p["sku"] for p in page2["products"]}
            self.assertEqual(page1_skus & page2_skus, set())

    def test_find_customers_pagination(self):
        from apps.customers.models import Customer

        for i in range(4):
            Customer.objects.create(store=self.store, name=f"Pagey Customer {i}", email=f"pagey{i}@x.com")
        with patch.object(tools, "SEARCH_RESULT_LIMIT", 2):
            page1, _ = tools._tool_find_customers(
                store=self.store, user=self.user, conversation=None, query="Pagey"
            )
            self.assertEqual(page1["total_count"], 4)
            self.assertTrue(page1["truncated"])
            page2, _ = tools._tool_find_customers(
                store=self.store, user=self.user, conversation=None, query="Pagey", offset=page1["next_offset"]
            )
            page1_ids = {c["id"] for c in page1["customers"]}
            page2_ids = {c["id"] for c in page2["customers"]}
            self.assertEqual(page1_ids & page2_ids, set())
            self.assertEqual(len(page1_ids) + len(page2_ids), 4)

    def test_find_products_pagination(self):
        for i in range(4):
            Product.objects.create(
                store=self.store, name=f"Pagey Product {i}", sku=f"PAGEY-{i}", price=Decimal("1.00"),
                currency="USD", stock_quantity=10,
            )
        with patch.object(tools, "SEARCH_RESULT_LIMIT", 2):
            page1, _ = tools._tool_find_products(
                store=self.store, user=self.user, conversation=None, query="Pagey"
            )
            self.assertEqual(page1["total_count"], 4)
            self.assertTrue(page1["truncated"])
            page2, _ = tools._tool_find_products(
                store=self.store, user=self.user, conversation=None, query="Pagey", offset=page1["next_offset"]
            )
            page1_skus = {p["sku"] for p in page1["products"]}
            page2_skus = {p["sku"] for p in page2["products"]}
            self.assertEqual(page1_skus & page2_skus, set())
            self.assertEqual(len(page1_skus) + len(page2_skus), 4)

    def test_list_customer_orders_pagination(self):
        self._extra_orders(5)
        with patch.object(tools, "CUSTOMER_ORDERS_LIMIT", 2):
            page1, _ = tools._tool_list_customer_orders(
                store=self.store, user=self.user, conversation=None, customer_id=self.customer.id
            )
            self.assertEqual(page1["total_orders"], 5)
            self.assertTrue(page1["truncated"])
            page2, _ = tools._tool_list_customer_orders(
                store=self.store,
                user=self.user,
                conversation=None,
                customer_id=self.customer.id,
                offset=page1["next_offset"],
            )
            # by_payment_status/total_orders always describe the whole customer, not just the page.
            self.assertEqual(page2["total_orders"], 5)
            self.assertEqual(page1["by_payment_status"], page2["by_payment_status"])
            page1_ids = {o["order_id"] for o in page1["orders"]}
            page2_ids = {o["order_id"] for o in page2["orders"]}
            self.assertEqual(page1_ids & page2_ids, set())

    def test_negative_offset_clamps_to_the_first_page_instead_of_erroring(self):
        self._extra_orders(3)
        with patch.object(tools, "STORE_LIST_LIMIT", 2):
            first_page, _ = tools._tool_list_unpaid_orders(store=self.store, user=self.user, conversation=None)
            negative, _ = tools._tool_list_unpaid_orders(
                store=self.store, user=self.user, conversation=None, offset=-5
            )
            self.assertEqual(
                [o["order_id"] for o in negative["orders"]], [o["order_id"] for o in first_page["orders"]]
            )
