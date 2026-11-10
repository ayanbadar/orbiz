from django.urls import path

from apps.dashboard import views as v

urlpatterns = [
    path("summary/", v.PlatformDashboardView.as_view(), name="admin-dashboard-summary"),
]
