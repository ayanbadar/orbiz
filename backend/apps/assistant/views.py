import json

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
    permission_resource = "assistant"


def _source_labels(output_json: str) -> list[str]:
    """
    The order number / customer name a single tool result named, straight from its own
    top-level fields — never a nested list (e.g. list_recent_orders' `orders: [...]`, which
    every tool result already treats as a browse, not a fact about one record) and never a
    tool/function name.
    """
    try:
        data = json.loads(output_json)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, dict):
        return []
    labels: list[str] = []
    order_number = data.get("order_number")
    if isinstance(order_number, str) and order_number:
        labels.append(order_number)
    customer = data.get("customer")
    if isinstance(customer, dict) and isinstance(customer.get("name"), str) and customer["name"]:
        labels.append(customer["name"])
    elif isinstance(data.get("customer_id"), int) and isinstance(data.get("name"), str) and data["name"]:
        labels.append(data["name"])
    return labels


def _attach_sources(all_messages: list[AssistantMessage]) -> None:
    """
    Stashes `_sources` (order numbers / customer names, deduped) on each ASSISTANT message,
    read from the FUNCTION_CALL_OUTPUT rows since the message before it — i.e. this reply's own
    turn. Mutates the AssistantMessage instances in place; `_conversation_payload` serializes
    the same instances afterwards so the attribute is picked up. No schema change: nothing is
    persisted, this is computed fresh on every read.
    """
    pending: list[str] = []
    for msg in all_messages:
        if msg.item_type == AssistantMessage.ItemType.FUNCTION_CALL_OUTPUT:
            pending.extend(_source_labels(msg.content))
        elif msg.item_type == AssistantMessage.ItemType.MESSAGE:
            if msg.role == AssistantMessage.Role.ASSISTANT and pending:
                msg._sources = list(dict.fromkeys(pending))
            pending = []


# Every list/search tool already returns this same shape (tools._list_meta): a top-level
# orders/customers/products array plus total_count/truncated/next_offset. That uniform contract
# is also a reliable "this is a browsable list, not a one-off fact" signal — reuse it here
# instead of a per-tool-name allowlist, so a future list tool picks this up for free.
_LIST_RESULT_KINDS = ("orders", "customers", "products")

_TABLE_LABELS = {
    "list_unpaid_orders": "unpaid orders",
    "list_recent_orders": "recent orders",
    "list_low_stock_products": "low-stock products",
    "find_products": "matching products",
    "find_customers": "matching customers",
}


def _table_title(tool_name: str, kind: str, data: dict) -> str:
    shown = len(data.get(kind) or [])
    total = data.get("total_count")
    total = total if isinstance(total, int) else shown
    if tool_name == "list_customer_orders":
        customer_name = (data.get("customer") or {}).get("name") or "this customer"
        label = f"orders for {customer_name}"
    else:
        label = _TABLE_LABELS.get(tool_name, kind)
    return f"Showing {shown} of {total} {label}" if shown < total else f"{total} {label}"


def _view_all_filters(tool_name: str, data: dict, arguments: dict) -> dict[str, str]:
    """
    URL query params for the real Orders/Products/Customers page's own existing filters
    (nuqs-driven — see e.g. frontend's orders-page.tsx `q`/`payment_status`/`customer_id`), so
    "view all" lands on that exact same search instead of just the previewed page. Resolved
    from the tool's own output where possible (e.g. list_unpaid_orders' `payment_status_filter`
    already reflects what it actually searched, not just what was asked for); only the free-text
    `query` arg isn't echoed back in the output, so that one comes from `arguments`.
    """
    if tool_name == "list_customer_orders":
        customer_id = (data.get("customer") or {}).get("id")
        return {"customer_id": str(customer_id)} if isinstance(customer_id, int) else {}
    if tool_name == "list_unpaid_orders":
        status = data.get("payment_status_filter")
        return {"payment_status": status} if status in ("unpaid", "pending") else {}
    if tool_name == "list_low_stock_products":
        return {"low_stock": "true"}
    if tool_name == "list_recent_orders":
        filters: dict[str, str] = {}
        after = (arguments or {}).get("created_after")
        before = (arguments or {}).get("created_before")
        if isinstance(after, str) and after:
            filters["created_after"] = after
        if isinstance(before, str) and before:
            filters["created_before"] = before
        return filters
    if tool_name in ("find_products", "find_customers"):
        query = (arguments or {}).get("query")
        return {"q": query} if isinstance(query, str) and query else {}
    return {}


def _result_table(tool_name: str, output_json: str, arguments: dict) -> dict | None:
    """
    A list/search tool's own structured rows, straight from its JSON output — so the frontend
    can render a real table instead of the model retyping every row into prose. None when this
    output isn't a paginated list result (tools._list_meta's shape).
    """
    try:
        data = json.loads(output_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("total_count"), int):
        return None
    for kind in _LIST_RESULT_KINDS:
        rows = data.get(kind)
        if isinstance(rows, list) and rows and all(isinstance(row, dict) for row in rows):
            return {
                "tool": tool_name,
                "kind": kind,
                "title": _table_title(tool_name, kind, data),
                "rows": rows,
                "total_count": data["total_count"],
                "truncated": bool(data.get("truncated", False)),
                "next_offset": data.get("next_offset"),
                "view_all": _view_all_filters(tool_name, data, arguments),
            }
    return None


def _attach_result_tables(all_messages: list[AssistantMessage]) -> None:
    """
    Stashes `_tables` (structured list results from this reply's own tool calls) on each
    ASSISTANT message — same timing/pattern as `_attach_sources`, just richer data. A
    FUNCTION_CALL_OUTPUT row doesn't carry its own tool_name/arguments (see services.run_turn),
    so this first maps call_id -> (tool_name, arguments) from the paired FUNCTION_CALL row.
    """
    calls: dict[str, tuple[str, dict]] = {}
    pending: list[dict] = []
    for msg in all_messages:
        if msg.item_type == AssistantMessage.ItemType.FUNCTION_CALL:
            calls[msg.call_id] = (msg.tool_name, msg.tool_arguments or {})
        elif msg.item_type == AssistantMessage.ItemType.FUNCTION_CALL_OUTPUT:
            tool_name, arguments = calls.get(msg.call_id, ("", {}))
            table = _result_table(tool_name, msg.content, arguments)
            if table is not None:
                pending.append(table)
        elif msg.item_type == AssistantMessage.ItemType.MESSAGE:
            if msg.role == AssistantMessage.Role.ASSISTANT and pending:
                msg._tables = pending
            pending = []


def _conversation_payload(conversation) -> dict:
    all_messages = list(conversation.messages.all())
    _attach_sources(all_messages)
    _attach_result_tables(all_messages)
    messages = [m for m in all_messages if m.item_type == AssistantMessage.ItemType.MESSAGE]
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
            conversation = services.get_conversation(conversation_id=conversation_id, store=self.store)
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
        return services.list_conversations(store=self.store).prefetch_related("messages")


class AssistantConversationDetailView(AssistantStoreMixin, APIView):
    @extend_schema(
        tags=["assistant"],
        summary="Get a conversation",
        responses={200: AssistantConversationSerializer},
    )
    def get(self, request, pk):
        conversation = services.get_conversation(conversation_id=pk, store=self.store)
        return Response(_conversation_payload(conversation))

    @extend_schema(
        tags=["assistant"],
        summary="Delete a conversation",
        request=None,
        responses={204: None},
    )
    def delete(self, request, pk):
        services.delete_conversation(conversation_id=pk, store=self.store)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
    permission_action = "update"

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
    permission_action = "update"

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
