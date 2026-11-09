from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assistant import services
from apps.assistant.models import AssistantAction, AssistantMessage
from apps.assistant.serializers import (
    ActionConfirmSerializer,
    AssistantActionSerializer,
    AssistantActivitySerializer,
    AssistantConversationSerializer,
    AssistantConversationSummarySerializer,
    AssistantDigestSerializer,
    AssistantMessageInputSerializer,
    AssistantMessageSerializer,
    AssistantTurnResponseSerializer,
)
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
from apps.stores.mixins import StoreScopedMixin


class AssistantStoreMixin(StoreScopedMixin):
    missing_store_message = "Create a store workspace before using Orbiz AI."


def _conversation_payload(conversation) -> dict:
    messages = conversation.messages.filter(item_type=AssistantMessage.ItemType.MESSAGE)
    # Every proposal this conversation has ever made, not just pending ones — resolved
    # proposals stay visible in their original spot so the seller isn't left wondering
    # what happened to a card they already acted on.
    actions = conversation.actions.select_related("order").order_by("created_at")
    # Every order this conversation created, via its link row — not re-derived from
    # whatever the model happened to touch most recently, so the card stays put.
    order_links = conversation.created_order_links.select_related(
        "order", "order__customer"
    ).prefetch_related("order__lines__product", "order__events").order_by("created_at")
    orders = [link.order for link in order_links]
    return {
        "conversation_id": conversation.id,
        "messages": AssistantMessageSerializer(messages, many=True).data,
        "actions": AssistantActionSerializer(actions, many=True).data,
        "orders": OrderSerializer(orders, many=True).data,
    }


class AssistantMessageView(AssistantStoreMixin, APIView):
    throttle_scope = "assistant"

    @extend_schema(
        tags=["assistant"],
        summary="Send a message to Orbiz AI",
        request=AssistantMessageInputSerializer,
        responses={200: AssistantTurnResponseSerializer},
    )
    def post(self, request):
        serializer = AssistantMessageInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation_id = serializer.validated_data.get("conversation_id")
        if conversation_id:
            conversation = services.get_conversation(
                conversation_id=conversation_id, store=self.store, user=request.user
            )
        else:
            conversation = services.new_conversation(store=self.store, user=request.user)

        result = services.run_turn(
            store=self.store,
            user=request.user,
            conversation=conversation,
            user_message=serializer.validated_data["message"],
        )

        created_orders = Order.objects.filter(
            store=self.store, pk__in=result["created_order_ids"]
        )
        pending_actions = AssistantAction.objects.filter(
            store=self.store, pk__in=result["pending_action_ids"]
        )
        return Response(
            {
                "conversation_id": conversation.id,
                "reply": result["reply"],
                "created_orders": OrderSerializer(created_orders, many=True).data,
                "pending_actions": AssistantActionSerializer(pending_actions, many=True).data,
            }
        )


class AssistantConversationListView(AssistantStoreMixin, generics.ListAPIView):
    serializer_class = AssistantConversationSummarySerializer

    @extend_schema(tags=["assistant"], summary="List conversations")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["assistant"],
        summary="Start a new conversation",
        request=None,
        responses={201: AssistantConversationSerializer},
    )
    def post(self, request):
        conversation = services.new_conversation(store=self.store, user=request.user)
        return Response(_conversation_payload(conversation), status=status.HTTP_201_CREATED)

    def get_queryset(self):
        return services.list_conversations(store=self.store, user=self.request.user).prefetch_related(
            "messages"
        )


class AssistantConversationDetailView(AssistantStoreMixin, APIView):
    @extend_schema(
        tags=["assistant"],
        summary="Get a conversation",
        responses={200: AssistantConversationSerializer},
    )
    def get(self, request, pk):
        conversation = services.get_conversation(conversation_id=pk, store=self.store, user=request.user)
        return Response(_conversation_payload(conversation))


class AssistantActionListView(AssistantStoreMixin, generics.ListAPIView):
    serializer_class = AssistantActionSerializer

    @extend_schema(tags=["assistant"], summary="List proposed actions")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = AssistantAction.objects.filter(store=self.store).select_related("order")
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs


class AssistantActionConfirmView(AssistantStoreMixin, APIView):
    throttle_scope = "assistant"

    @extend_schema(
        tags=["assistant"],
        summary="Confirm a proposed action",
        request=ActionConfirmSerializer,
        responses={200: AssistantActionSerializer},
    )
    def post(self, request, pk):
        serializer = ActionConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = services.confirm_action(
            action_id=pk, store=self.store, user=request.user, overrides=serializer.validated_data
        )
        return Response(AssistantActionSerializer(action).data)


class AssistantActionRejectView(AssistantStoreMixin, APIView):
    throttle_scope = "assistant"

    @extend_schema(
        tags=["assistant"],
        summary="Reject a proposed action",
        request=None,
        responses={200: AssistantActionSerializer},
    )
    def post(self, request, pk):
        action = services.reject_action(action_id=pk, store=self.store, user=request.user)
        return Response(AssistantActionSerializer(action).data)


class AssistantDigestView(AssistantStoreMixin, APIView):
    @extend_schema(
        tags=["assistant"],
        summary="Today's digest (no LLM call)",
        responses={200: AssistantDigestSerializer},
    )
    def get(self, request):
        return Response(services.digest(store=self.store))


class AssistantActivityListView(AssistantStoreMixin, generics.ListAPIView):
    serializer_class = AssistantActivitySerializer

    @extend_schema(tags=["assistant"], summary="List Orbiz AI activity")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return services.activity_queryset(store=self.store)
