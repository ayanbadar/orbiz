from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny, IsAuthenticated


def health(_request):
    return JsonResponse({"status": "ok"})


class SchemaView(SpectacularAPIView):
    """Public schema only in DEBUG; authenticated elsewhere."""

    def get_authenticators(self):
        if settings.DEBUG:
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if settings.DEBUG:
            return [AllowAny()]
        return [IsAuthenticated()]


class SwaggerView(SpectacularSwaggerView):
    def get_authenticators(self):
        if settings.DEBUG:
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if settings.DEBUG:
            return [AllowAny()]
        return [IsAuthenticated()]


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/stores/", include("apps.stores.urls")),
    path("api/v1/products/", include("apps.products.urls")),
    path("api/v1/customers/", include("apps.customers.urls")),
    path("api/v1/orders/", include("apps.orders.urls")),
    path("api/schema/", SchemaView.as_view(), name="schema"),
    path(
        "api/docs/",
        SwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
