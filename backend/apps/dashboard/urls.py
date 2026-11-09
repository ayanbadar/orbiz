from django.urls import path

from apps.dashboard import views as v

urlpatterns = [
    path("summary/", v.StoreDashboardView.as_view(), name="dashboard-summary"),
]
