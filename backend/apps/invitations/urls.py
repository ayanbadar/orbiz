from django.urls import path

from apps.invitations import views as v

# Literal and integer routes come before the catch-all <token> routes.
urlpatterns = [
    path("", v.StaffInvitationListCreateView.as_view(), name="invitations"),
    path("<int:pk>/", v.StaffInvitationDetailView.as_view(), name="invitation-detail"),
    path("store-admins/", v.StoreAdminInvitationListCreateView.as_view(), name="store-admin-invitations"),
    path(
        "store-admins/<int:pk>/",
        v.StoreAdminInvitationDetailView.as_view(),
        name="store-admin-invitation-detail",
    ),
    path("<str:token>/", v.InvitationPreviewView.as_view(), name="invitation-preview"),
    path("<str:token>/accept/", v.InvitationAcceptView.as_view(), name="invitation-accept"),
]
