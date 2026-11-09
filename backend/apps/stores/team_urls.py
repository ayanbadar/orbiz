from django.urls import path

from apps.stores import team_views as v

urlpatterns = [
    path("users/", v.TeamUserListView.as_view(), name="team-users"),
    path("users/<int:pk>/", v.TeamUserDetailView.as_view(), name="team-user-detail"),
    path("roles/", v.RoleListCreateView.as_view(), name="team-roles"),
    path("roles/<int:pk>/", v.RoleDetailView.as_view(), name="team-role-detail"),
    path("permissions/", v.PermissionCatalogView.as_view(), name="team-permissions"),
]
