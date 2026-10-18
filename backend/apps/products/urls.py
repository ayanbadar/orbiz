from django.urls import path

from apps.products.views import (
    AdjustStockView,
    Channel3SearchView,
    ImportFromChannel3View,
    ProductAdjustmentsView,
    ProductDetailView,
    ProductListCreateView,
)

urlpatterns = [
    path("", ProductListCreateView.as_view(), name="product-list-create"),
    path("channel3/search/", Channel3SearchView.as_view(), name="product-channel3-search"),
    path("import-from-channel3/", ImportFromChannel3View.as_view(), name="product-import-channel3"),
    path("<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("<int:pk>/adjust-stock/", AdjustStockView.as_view(), name="product-adjust-stock"),
    path("<int:pk>/adjustments/", ProductAdjustmentsView.as_view(), name="product-adjustments"),
]
