from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard import services
from apps.dashboard.serializers import (
    PlatformDashboardSerializer,
    StoreDashboardSerializer,
)
from apps.stores.mixins import PlatformAdminMixin, StoreScopedMixin

RANGE_PARAMETER = OpenApiParameter(
    "range", str, enum=["7d", "30d", "90d"], description="Reporting period. Defaults to 30d."
)


def _range(request) -> str:
    # Unknown values fall back to the default instead of failing the dashboard.
    return services.parse_range(request.query_params.get("range"))


class StoreDashboardView(StoreScopedMixin, APIView):
    """Sales, orders, customers and stock for the caller's store."""

    permission_resource = "orders"

    @extend_schema(
        tags=["dashboard"],
        summary="Store dashboard summary",
        parameters=[RANGE_PARAMETER],
        responses=StoreDashboardSerializer,
    )
    def get(self, request):
        data = services.store_summary(self.store, _range(request))
        return Response(StoreDashboardSerializer(data).data)


class PlatformDashboardView(PlatformAdminMixin, APIView):
    """Platform-wide numbers for the super admin."""

    @extend_schema(
        tags=["dashboard"],
        summary="Platform dashboard summary",
        parameters=[RANGE_PARAMETER],
        responses=PlatformDashboardSerializer,
    )
    def get(self, request):
        data = services.platform_summary(_range(request))
        return Response(PlatformDashboardSerializer(data).data)
