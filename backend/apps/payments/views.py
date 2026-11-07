import json
import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import ConflictError
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
from apps.payments import paypal as paypal_client
from apps.payments.serializers import (
    InvoiceRequestSerializer,
    PaymentCheckoutDetailSerializer,
    PaymentCheckoutSerializer,
    RefundRequestSerializer,
    paypal_status_flags,
)
from apps.payments.services import (
    cancel_invoice_for_order,
    capture_checkout,
    create_checkout,
    get_checkout_for_store,
    receive_webhook,
    refund_order,
    send_invoice_for_order,
)
from apps.payments.tasks import process_paypal_webhook_event
from apps.stores.mixins import StoreScopedMixin

logger = logging.getLogger(__name__)


class PaymentOrderMixin(StoreScopedMixin):
    missing_store_message = "Create a store workspace before managing payments."

    def get_order(self, order_id: int) -> Order:
        return generics.get_object_or_404(
            Order.objects.filter(store=self.store),
            pk=order_id,
        )

    def order_response(self, order_id: int) -> Response:
        order = (
            Order.objects.filter(store=self.store, pk=order_id)
            .select_related("customer")
            .prefetch_related("lines", "events", "paypal_checkouts")
            .get()
        )
        return Response(OrderSerializer(order).data)


class PaymentCheckoutCreateView(PaymentOrderMixin, APIView):
    throttle_scope = "payments"

    @extend_schema(
        tags=["payments"],
        summary="Create PayPal Sandbox checkout for an order",
        request=None,
        responses={201: PaymentCheckoutSerializer},
    )
    def post(self, request, order_id: int):
        self.get_order(order_id)
        checkout = create_checkout(
            order_id=order_id,
            store=self.store,
            user=request.user,
        )
        return Response(
            PaymentCheckoutSerializer(checkout).data,
            status=status.HTTP_201_CREATED,
        )


class PaymentCheckoutCaptureView(PaymentOrderMixin, APIView):
    throttle_scope = "payments"

    @extend_schema(
        tags=["payments"],
        summary="Capture PayPal Sandbox checkout for an order",
        request=None,
        responses={200: OrderSerializer},
    )
    def post(self, request, order_id: int):
        self.get_order(order_id)
        order, _checkout = capture_checkout(
            order_id=order_id,
            store=self.store,
            user=request.user,
        )
        return self.order_response(order.pk)


class PaymentRefundView(PaymentOrderMixin, APIView):
    throttle_scope = "payments"

    @extend_schema(
        tags=["payments"],
        summary="Refund an order's PayPal Sandbox payment (full or partial)",
        request=RefundRequestSerializer,
        responses={200: OrderSerializer},
    )
    def post(self, request, order_id: int):
        serializer = RefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.get_order(order_id)
        order = refund_order(
            order_id=order_id,
            store=self.store,
            user=request.user,
            amount=serializer.validated_data.get("amount"),
            note_to_payer=serializer.validated_data["note_to_payer"],
        )
        return self.order_response(order.pk)


class PaymentInvoiceCreateView(PaymentOrderMixin, APIView):
    throttle_scope = "payments"

    @extend_schema(
        tags=["payments"],
        summary="Create and send a PayPal Sandbox invoice for an order",
        request=InvoiceRequestSerializer,
        responses={201: OrderSerializer},
    )
    def post(self, request, order_id: int):
        serializer = InvoiceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.get_order(order_id)
        send_invoice_for_order(
            order_id=order_id,
            store=self.store,
            user=request.user,
            recipient_email=serializer.validated_data["recipient_email"],
        )
        response = self.order_response(order_id)
        response.status_code = status.HTTP_201_CREATED
        return response


class PaymentInvoiceCancelView(PaymentOrderMixin, APIView):
    throttle_scope = "payments"

    @extend_schema(
        tags=["payments"],
        summary="Cancel the open PayPal Sandbox invoice for an order",
        request=None,
        responses={200: OrderSerializer},
    )
    def post(self, request, order_id: int):
        self.get_order(order_id)
        cancel_invoice_for_order(
            order_id=order_id,
            store=self.store,
            user=request.user,
        )
        return self.order_response(order_id)


class PaymentCheckoutDetailView(PaymentOrderMixin, APIView):
    @extend_schema(
        tags=["payments"],
        summary="Latest PayPal checkout for an order",
        responses={200: PaymentCheckoutDetailSerializer},
    )
    def get(self, request, order_id: int):
        self.get_order(order_id)
        checkout = get_checkout_for_store(order_id=order_id, store=self.store)
        payload = {
            **paypal_status_flags(),
            "checkout": PaymentCheckoutSerializer(checkout).data if checkout else None,
        }
        return Response(payload)


class PayPalWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["payments"],
        summary="PayPal webhook receiver (signature verified)",
        request=None,
        responses={200: None},
    )
    def post(self, request):
        raw_body = request.body
        header_map = {k.upper(): v for k, v in request.headers.items()}
        # Normalize common PayPal header spellings for the client.
        for key, value in list(request.headers.items()):
            header_map[key] = value
            header_map[key.upper()] = value

        try:
            verified = paypal_client.verify_webhook(headers=header_map, body=raw_body)
        except Exception as exc:
            logger.warning("PayPal webhook verification error: %s", type(exc).__name__)
            return Response(
                {"detail": "Webhook verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not verified:
            return Response(
                {"detail": "Invalid PayPal webhook signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response(
                {"detail": "Invalid JSON body."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_id = payload.get("id") or ""
        event_type = payload.get("event_type") or ""
        try:
            event = receive_webhook(
                event_id=event_id,
                event_type=event_type,
                payload=payload,
            )
        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if event.processed_at is None:
            event_pk = event.pk
            transaction.on_commit(
                lambda: process_paypal_webhook_event.delay(event_pk)
            )

        return Response({"status": "ok"}, status=status.HTTP_200_OK)
