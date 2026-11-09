from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing import services
from apps.billing.models import PLAN_PERIOD_DAYS, PLAN_PRICE_CENTS
from apps.billing.serializers import BillingSerializer, CheckoutSerializer
from apps.stores.permissions import IsStoreAdmin

TAGS = ["billing"]


class BillingMixin:
    permission_classes = [IsAuthenticated, IsStoreAdmin]


def _billing_payload(store) -> dict:
    subscription = services.get_or_create_subscription(store)
    return {
        "plan_price_cents": PLAN_PRICE_CENTS,
        "plan_period_days": PLAN_PERIOD_DAYS,
        "store_status": store.status,
        "subscription_status": subscription.status,
        "current_period_end": subscription.current_period_end,
        "payments": store.payments.all()[:20],
    }


class BillingView(BillingMixin, APIView):
    @extend_schema(tags=TAGS, summary="Subscription status and payment history", responses=BillingSerializer)
    def get(self, request):
        return Response(BillingSerializer(_billing_payload(request.store)).data)


class CheckoutView(BillingMixin, APIView):
    throttle_scope = "writes"

    @extend_schema(
        tags=TAGS,
        summary="Pay the $5 plan (mock — no real charge)",
        request=CheckoutSerializer,
        responses=BillingSerializer,
    )
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Failure simulation is a dev/demo aid only.
        simulate = serializer.validated_data["simulate_failure"] and settings.DEBUG
        services.mock_charge(store=request.store, simulate_failure=simulate)
        request.store.refresh_from_db()
        return Response(BillingSerializer(_billing_payload(request.store)).data, status=status.HTTP_201_CREATED)


class CancelView(BillingMixin, APIView):
    throttle_scope = "writes"

    @extend_schema(tags=TAGS, summary="Cancel renewal", request=None, responses=BillingSerializer)
    def post(self, request):
        services.cancel_subscription(store=request.store)
        return Response(BillingSerializer(_billing_payload(request.store)).data)
