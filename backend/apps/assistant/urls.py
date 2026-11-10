from django.urls import path

from apps.assistant.views import (
    AssistantActionConfirmView,
    AssistantActionListView,
    AssistantActionRejectView,
    AssistantActivityListView,
    AssistantConversationDetailView,
    AssistantConversationListView,
    AssistantDigestView,
    AssistantMessageView,
)

urlpatterns = [
    path("messages/", AssistantMessageView.as_view(), name="assistant-messages"),
    path(
        "conversations/",
        AssistantConversationListView.as_view(),
        name="assistant-conversation-list",
    ),
    path(
        "conversations/<int:pk>/",
        AssistantConversationDetailView.as_view(),
        name="assistant-conversation-detail",
    ),
    path("actions/", AssistantActionListView.as_view(), name="assistant-action-list"),
    path(
        "actions/<int:pk>/confirm/",
        AssistantActionConfirmView.as_view(),
        name="assistant-action-confirm",
    ),
    path(
        "actions/<int:pk>/reject/",
        AssistantActionRejectView.as_view(),
        name="assistant-action-reject",
    ),
    path("digest/", AssistantDigestView.as_view(), name="assistant-digest"),
    path("activity/", AssistantActivityListView.as_view(), name="assistant-activity"),
]
