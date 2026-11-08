from unittest.mock import patch

import httpx
from django.test import SimpleTestCase
from rest_framework import status

from apps.common.exceptions import BadGatewayError
from apps.orders.models import Order, OrderEvent
from apps.payments import paypal
from apps.payments.models import PaymentCheckout
from apps.payments.tests.base import PayPalTestCase

CLIENT = "apps.payments.services.paypal_client"


class PayPalErrorMappingTests(SimpleTestCase):
    def test_order_not_approved_422_becomes_a_readable_message_with_its_issue_code(self):
        response = httpx.Response(
            422,
            json={
                "name": "UNPROCESSABLE_ENTITY",
                "message": (
                    "The requested action could not be performed, semantically incorrect, "
                    "or failed business validation."
                ),
                "details": [{"issue": "ORDER_NOT_APPROVED"}],
            },
        )
        with (
            patch.object(paypal, "_require_configured"),
            patch.object(paypal, "_auth_headers", return_value={}),
            patch("apps.payments.paypal.httpx.Client") as client,
        ):
            client.return_value.__enter__.return_value.request.return_value = response
            with self.assertRaises(BadGatewayError) as raised:
                paypal.capture_order(paypal_order_id="PP-1")

        self.assertIn("hasn't approved", raised.exception.message)
        self.assertNotIn("semantically incorrect", raised.exception.message)
        self.assertEqual(raised.exception.extra["paypal_issue"], "ORDER_NOT_APPROVED")


class CaptureBeforeApprovalTests(PayPalTestCase):
    def open_checkout(self, order_id: int) -> PaymentCheckout:
        return PaymentCheckout.objects.create(
            order_id=order_id,
            paypal_order_id="PP-1",
            status=PaymentCheckout.Status.CREATED,
            approve_url="https://paypal.example/approve",
            amount="49.00",
            currency="USD",
        )

    @patch(f"{CLIENT}.capture_order")
    def test_capturing_before_the_buyer_approves_is_a_readable_conflict(self, capture):
        capture.side_effect = BadGatewayError(
            "The buyer hasn't approved this payment on PayPal yet.",
            extra={"paypal_issue": "ORDER_NOT_APPROVED"},
        )
        order_id = self.confirmed_order()
        checkout = self.open_checkout(order_id)

        response = self.client.post(
            f"/api/v1/payments/orders/{order_id}/capture/", {}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "order_not_approved")
        self.assertIn("hasn't approved", response.data["detail"])
        # Nothing is marked failed: the buyer can still approve and the seller capture again.
        checkout.refresh_from_db()
        self.assertEqual(checkout.status, PaymentCheckout.Status.CREATED)
        self.assertEqual(checkout.last_error, "")
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "pending")
        self.assertFalse(
            OrderEvent.objects.filter(
                order_id=order_id, message__startswith="PayPal Sandbox capture failed"
            ).exists()
        )

    @patch(f"{CLIENT}.capture_order")
    def test_capturing_again_after_the_buyer_approves_works(self, capture):
        capture.side_effect = [
            BadGatewayError("not yet", extra={"paypal_issue": "ORDER_NOT_APPROVED"}),
            {
                "id": "PP-1",
                "status": "COMPLETED",
                "capture_id": "CAP-1",
                "capture_status": "COMPLETED",
                "raw": {},
            },
        ]
        order_id = self.confirmed_order()
        self.open_checkout(order_id)
        url = f"/api/v1/payments/orders/{order_id}/capture/"

        first = self.client.post(url, {}, format="json")
        second = self.client.post(url, {}, format="json")

        self.assertEqual(first.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["payment_status"], "paid")

    @patch(f"{CLIENT}.capture_order")
    def test_other_paypal_failures_still_mark_the_checkout_failed(self, capture):
        capture.side_effect = BadGatewayError(
            "PayPal rejected the payment request.", extra={"paypal_issue": "INSTRUMENT_DECLINED"}
        )
        order_id = self.confirmed_order()
        checkout = self.open_checkout(order_id)

        response = self.client.post(
            f"/api/v1/payments/orders/{order_id}/capture/", {}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        checkout.refresh_from_db()
        self.assertEqual(checkout.status, PaymentCheckout.Status.FAILED)
        self.assertEqual(Order.objects.get(pk=order_id).payment_status, "failed")
