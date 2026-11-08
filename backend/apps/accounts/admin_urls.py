from django.urls import path

from apps.accounts import admin_views as v

urlpatterns = [
    path("", v.AdminUserListView.as_view(), name="admin-users"),
    path("<int:pk>/", v.AdminUserDetailView.as_view(), name="admin-user-detail"),
]
