from django.urls import path

from apps.stores.views import (
    StoreDetailView,
    StoreListCreateView,
    StoreMeView,
)

urlpatterns = [
    path("", StoreListCreateView.as_view(), name="store-list-create"),
    path("me/", StoreMeView.as_view(), name="store-me"),
    path("<int:pk>/", StoreDetailView.as_view(), name="store-detail"),
]
