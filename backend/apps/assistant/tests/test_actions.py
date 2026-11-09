from unittest.mock import patch

from rest_framework import status

from apps.assistant import tools
from apps.assistant.models import AssistantAction
from apps.assistant.services import confirm_action, reject_action
from apps.assistant.tests.base import AssistantTestCase
from apps.orders.models import Order, OrderEvent
from apps.payments.models import PaymentCheckout, PaymentInvoice
from apps.products.models import Product


class ProposeOnlyTests(AssistantTestCase):
    """Propose tools must create a pending row and touch nothing else."""

    @patch("apps.payments.services.paypal_client.refund_capture")
    def test_propose_refund_makes_no_service_call(self, mock_refund):
        order_id = self.paid_order()
        output, side_effect = tools._tool_propose_refund(
            store=self.store, user=self.user, conversation=None, order_id=order_id, amount=None
        )
        self.assertNotIn("error", output)
        action = AssistantAction.objects.get(pk=side_effect["action_id"])
        self.assertEqual(action.status, AssistantAction.Status.PENDING)
        self.assertEqual(action.action_type, AssistantAction.ActionType.REFUND)
        mock_refund.assert_not_called()

        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID, "unconfirmed proposal must not refund")

    @patch("apps.payments.services.paypal_client.capture_order")
    def test_propose_capture_makes_no_service_call(self, mock_capture):
        order_id = self.confirmed_order()
        output, side_effect = tools._tool_propose_capture_checkout(
            store=self.store, user=self.user, conversation=None, order_id=order_id
        )
        self.assertNotIn("error", output)
        action = AssistantAction.objects.get(pk=side_effect["action_id"])
        self.assertEqual(action.status, AssistantAction.Status.PENDING)
        mock_capture.assert_not_called()

    @patch("apps.products.channel3.retrieve_product")
    def test_propose_import_product_caches_channel3_payload(self, mock_retrieve):
        mock_retrieve.return_value = {
            "channel3_product_id": "C3-1",
            "title": "Nike Air Force 1",
            "description": "",
            "image_url": "",
            "suggested_price": "110.00",
            "currency": "USD",
            "brand": "Nike",
            "availability": "InStock",
        }
        output, side_effect = tools._tool_propose_import_product(
            store=self.store,
            user=self.user,
            conversation=None,
            channel3_product_id="C3-1",
            sku="NIKE-AF1",
            price="120.00",
            stock_quantity=5,
        )
        self.assertNotIn("error", output)
        action = AssistantAction.objects.get(pk=side_effect["action_id"])
        self.assertEqual(action.action_type, AssistantAction.ActionType.IMPORT_PRODUCT)
        self.assertEqual(action.payload["channel3_payload"]["title"], "Nike Air Force 1")
        self.assertFalse(Product.objects.filter(sku="NIKE-AF1").exists())

    def test_offer_payment_method_choice_makes_no_service_call(self):
        order_id = self.confirmed_order()
        output, side_effect = tools._tool_offer_payment_method_choice(
            store=self.store, user=self.user, conversation=None, order_id=order_id
        )
        self.assertNotIn("error", output)
        action = AssistantAction.objects.get(pk=side_effect["action_id"])
        self.assertEqual(action.status, AssistantAction.Status.PENDING)
        self.assertEqual(action.action_type, AssistantAction.ActionType.REQUEST_PAYMENT)
        self.assertFalse(PaymentCheckout.objects.filter(order_id=order_id).exists())


class ConfirmRejectTests(AssistantTestCase):
    @patch("apps.payments.services.paypal_client.refund_capture")
    def test_confirm_refund_executes_and_notes_origin(self, mock_refund):
        mock_refund.return_value = {"id": "REFUND-1", "status": "COMPLETED"}
        order_id = self.paid_order()
        action = AssistantAction.objects.create(
            store=self.store, order_id=order_id, action_type=AssistantAction.ActionType.REFUND,
            payload={}, created_by=self.user,
        )
        confirmed = confirm_action(action_id=action.id, store=self.store, user=self.user)
        self.assertEqual(confirmed.status, AssistantAction.Status.CONFIRMED)

        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.payment_status, Order.PaymentStatus.REFUNDED)
        note = OrderEvent.objects.filter(order=order, origin=OrderEvent.Origin.ASSISTANT).first()
        self.assertIsNotNone(note)

    def test_confirm_twice_raises_conflict(self):
        order_id = self.paid_order()
        action = AssistantAction.objects.create(
            store=self.store, order_id=order_id, action_type=AssistantAction.ActionType.REFUND,
            payload={}, created_by=self.user,
        )
        action.status = AssistantAction.Status.CONFIRMED
        action.save(update_fields=["status"])
        from apps.common.exceptions import ConflictError

        with self.assertRaises(ConflictError):
            confirm_action(action_id=action.id, store=self.store, user=self.user)

    def test_confirm_wrong_store_not_found(self):
        order_id = self.paid_order()
        action = AssistantAction.objects.create(
            store=self.store, order_id=order_id, action_type=AssistantAction.ActionType.REFUND,
            payload={}, created_by=self.user,
        )
        from apps.common.exceptions import NotFoundError

        with self.assertRaises(NotFoundError):
            confirm_action(action_id=action.id, store=self.other_store, user=self.other)

    @patch("apps.products.channel3.retrieve_product")
    def test_confirm_import_product_with_edited_fields(self, mock_retrieve):
        mock_retrieve.return_value = {
            "channel3_product_id": "C3-2",
            "title": "Gift Box",
            "description": "",
            "image_url": "",
            "suggested_price": "10.00",
            "currency": "USD",
        }
        output, side_effect = tools._tool_propose_import_product(
            store=self.store, user=self.user, conversation=None,
            channel3_product_id="C3-2", sku="GIFT-1", price="12.00", stock_quantity=3,
        )
        confirmed = confirm_action(
            action_id=side_effect["action_id"], store=self.store, user=self.user,
            overrides={"price": "15.00", "stock_quantity": 7},
        )
        self.assertEqual(confirmed.status, AssistantAction.Status.CONFIRMED)
        product = Product.objects.get(sku="GIFT-1")
        self.assertEqual(str(product.price), "15.00")
        self.assertEqual(product.stock_quantity, 7)

    @patch("apps.payments.services.paypal_client.create_order")
    def test_confirm_request_payment_with_checkout_method_creates_a_pay_now_link(self, mock_create):
        mock_create.return_value = {
            "id": "PP-CHECKOUT-1", "status": "CREATED",
            "approve_url": "https://sandbox.paypal.com/x", "raw": {},
        }
        order_id = self.confirmed_order()
        action = AssistantAction.objects.create(
            store=self.store, order_id=order_id, action_type=AssistantAction.ActionType.REQUEST_PAYMENT,
            payload={}, created_by=self.user,
        )
        confirmed = confirm_action(
            action_id=action.id, store=self.store, user=self.user, overrides={"method": "checkout"}
        )
        self.assertEqual(confirmed.status, AssistantAction.Status.CONFIRMED)
        self.assertEqual(confirmed.payload["method"], "checkout")
        self.assertTrue(PaymentCheckout.objects.filter(order_id=order_id).exists())

    @patch("apps.payments.services.paypal_client.create_order")
    def test_confirm_request_payment_with_email_link_method_emails_it(self, mock_create):
        from apps.notifications.models import EmailLog

        mock_create.return_value = {
            "id": "PP-CHECKOUT-2", "status": "CREATED",
            "approve_url": "https://sandbox.paypal.com/x", "raw": {},
        }
        order_id = self.confirmed_order()
        action = AssistantAction.objects.create(
            store=self.store, order_id=order_id, action_type=AssistantAction.ActionType.REQUEST_PAYMENT,
            payload={}, created_by=self.user,
        )
        confirmed = confirm_action(
            action_id=action.id, store=self.store, user=self.user, overrides={"method": "email_link"}
        )
        self.assertEqual(confirmed.status, AssistantAction.Status.CONFIRMED)
        self.assertTrue(EmailLog.objects.filter(recipient=self.customer.email).exists())

    @patch("apps.payments.services.paypal_client.get_invoice")
    @patch("apps.payments.services.paypal_client.send_invoice")
    @patch("apps.payments.services.paypal_client.create_invoice")
    def test_confirm_request_payment_with_invoice_method_sends_an_invoice(
        self, mock_create_invoice, mock_send_invoice, mock_get_invoice
    ):
        mock_create_invoice.return_value = {"id": "INV-REQ-1", "raw": {}}
        mock_get_invoice.return_value = {
            "id": "INV-REQ-1", "status": "SENT",
            "detail": {"metadata": {"recipient_view_url": "https://sandbox.paypal.com/invoice"}},
        }
        order_id = self.confirmed_order()
        action = AssistantAction.objects.create(
            store=self.store, order_id=order_id, action_type=AssistantAction.ActionType.REQUEST_PAYMENT,
            payload={}, created_by=self.user,
        )
        confirmed = confirm_action(
            action_id=action.id, store=self.store, user=self.user, overrides={"method": "invoice"}
        )
        self.assertEqual(confirmed.status, AssistantAction.Status.CONFIRMED)
        self.assertTrue(PaymentInvoice.objects.filter(order_id=order_id).exists())

    def test_confirm_request_payment_without_a_method_errors_and_stays_pending(self):
        from apps.common.exceptions import ApplicationError

        order_id = self.confirmed_order()
        action = AssistantAction.objects.create(
            store=self.store, order_id=order_id, action_type=AssistantAction.ActionType.REQUEST_PAYMENT,
            payload={}, created_by=self.user,
        )
        with self.assertRaises(ApplicationError):
            confirm_action(action_id=action.id, store=self.store, user=self.user)
        action.refresh_from_db()
        self.assertEqual(action.status, AssistantAction.Status.PENDING)

    def test_reject_marks_rejected_without_a_service_call(self):
        order_id = self.paid_order()
        action = AssistantAction.objects.create(
            store=self.store, order_id=order_id, action_type=AssistantAction.ActionType.REFUND,
            payload={}, created_by=self.user,
        )
        rejected = reject_action(action_id=action.id, store=self.store, user=self.user)
        self.assertEqual(rejected.status, AssistantAction.Status.REJECTED)
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID, "a rejected proposal must not refund")


class ActionEndpointTests(AssistantTestCase):
    @patch("apps.payments.services.paypal_client.refund_capture")
    def test_confirm_endpoint_happy_path(self, mock_refund):
        mock_refund.return_value = {"id": "REFUND-2", "status": "COMPLETED"}
        order_id = self.paid_order()
        action = AssistantAction.objects.create(
            store=self.store, order_id=order_id, action_type=AssistantAction.ActionType.REFUND,
            payload={}, created_by=self.user,
        )
        response = self.client.post(f"/api/v1/assistant/actions/{action.id}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "confirmed")

    def test_other_store_cannot_confirm(self):
        order_id = self.paid_order()
        action = AssistantAction.objects.create(
            store=self.store, order_id=order_id, action_type=AssistantAction.ActionType.REFUND,
            payload={}, created_by=self.user,
        )
        self.client.force_authenticate(self.other)
        response = self.client.post(f"/api/v1/assistant/actions/{action.id}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
