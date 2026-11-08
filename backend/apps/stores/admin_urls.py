from django.urls import path

from apps.stores import admin_views as v

urlpatterns = [
    path("", v.AdminStoreListView.as_view(), name="admin-stores"),
    path("<int:pk>/", v.AdminStoreDetailView.as_view(), name="admin-store-detail"),
]
