from django.urls import path

from apps.stores.views import (
    SetDefaultStoreView,
    StoreDetailView,
    StoreListCreateView,
    StoreMeView,
)

urlpatterns = [
    path("", StoreListCreateView.as_view(), name="store-list-create"),
    path("me/", StoreMeView.as_view(), name="store-me"),
    path("set-default/", SetDefaultStoreView.as_view(), name="store-set-default"),
    path("<int:pk>/", StoreDetailView.as_view(), name="store-detail"),
]
