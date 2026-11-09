from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.assistant.models import AssistantAction, AssistantConversation, AssistantMessage
from apps.orders.models import OrderEvent


class AssistantMessageInputSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, max_length=8000)
    conversation_id = serializers.IntegerField(required=False, min_value=1)


class AssistantResultTableSerializer(serializers.Serializer):
    """
    A list/search tool's own rows (views._result_table), so the frontend can render a real
    table instead of the model retyping every row. Row shape varies by kind/tool — left as
    plain dicts rather than modelled field-by-field.
    """

    tool = serializers.CharField()
    kind = serializers.ChoiceField(choices=["orders", "customers", "products"])
    title = serializers.CharField()
    rows = serializers.ListField(child=serializers.DictField())
    total_count = serializers.IntegerField()
    truncated = serializers.BooleanField()
    next_offset = serializers.IntegerField(required=False, allow_null=True)
    # Query params for the real Orders/Products/Customers page's own existing filters, so
    # "view all" opens that exact search — see views._view_all_filters.
    view_all = serializers.DictField(child=serializers.CharField(), default=dict)


class AssistantMessageSerializer(serializers.ModelSerializer):
    # Which orders/customers this reply's tool calls actually touched — order numbers and
    # customer names only, never a tool/function name. Computed at read time by
    # views._attach_sources and stashed as a plain attribute; empty for anything that wasn't
    # given one (user messages, and assistant replies that made no tool calls).
    source_records = serializers.SerializerMethodField()
    # Structured list-tool results from this reply's own turn — see views._attach_result_tables.
    result_tables = serializers.SerializerMethodField()

    class Meta:
        model = AssistantMessage
        fields = ["id", "role", "content", "created_at", "source_records", "result_tables"]

    def get_source_records(self, obj) -> list[str]:
        return getattr(obj, "_sources", [])

    @extend_schema_field(AssistantResultTableSerializer(many=True))
    def get_result_tables(self, obj) -> list[dict]:
        return getattr(obj, "_tables", [])


class AssistantActionOrderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    number = serializers.CharField()


class AssistantActionSerializer(serializers.ModelSerializer):
    order = AssistantActionOrderSerializer(read_only=True, allow_null=True)

    class Meta:
        model = AssistantAction
        fields = [
            "id",
            "action_type",
            "status",
            "order",
            "payload",
            "result_message",
            "created_at",
            "resolved_at",
        ]


class ActionConfirmSerializer(serializers.Serializer):
    """
    Optional edits merged into the stored proposal before it executes: a partial-refund
    amount, the product fields Channel3 can't supply (sku/price/stock), or which payment
    method the seller picked on a request_payment choice card. Unused fields for a given
    action_type are simply ignored.
    """

    amount = serializers.CharField(required=False, allow_blank=True)
    sku = serializers.CharField(required=False, allow_blank=True)
    price = serializers.CharField(required=False, allow_blank=True)
    stock_quantity = serializers.IntegerField(required=False)
    low_stock_threshold = serializers.IntegerField(required=False)
    method = serializers.ChoiceField(choices=["checkout", "invoice", "email_link"], required=False)


class AssistantActivitySerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source="order.id")
    order_number = serializers.CharField(source="order.number")

    class Meta:
        model = OrderEvent
        fields = ["id", "order_id", "order_number", "event_type", "message", "created_at"]


class AssistantConversationSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    messages = AssistantMessageSerializer(many=True)
    actions = AssistantActionSerializer(many=True)
    orders = serializers.ListField(child=serializers.DictField(), default=list)


class AssistantConversationSummarySerializer(serializers.ModelSerializer):
    preview = serializers.SerializerMethodField()

    class Meta:
        model = AssistantConversation
        fields = ["id", "preview", "created_at", "updated_at"]

    def get_preview(self, conversation: AssistantConversation) -> str:
        first_user_message = next(
            (m for m in conversation.messages.all() if m.item_type == "message" and m.role == "user"),
            None,
        )
        if first_user_message is None:
            return "New conversation"
        text = first_user_message.content.strip()
        return text[:60] + ("…" if len(text) > 60 else "")


class AssistantTurnResponseSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    reply = serializers.CharField()
    created_orders = serializers.ListField(child=serializers.DictField(), default=list)
    pending_actions = AssistantActionSerializer(many=True)


class DigestOrderRowSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    order_number = serializers.CharField()
    customer_name = serializers.CharField()
    total = serializers.CharField()
    currency = serializers.CharField()
    payment_status = serializers.CharField()
    days_old = serializers.IntegerField()


class DigestProductRowSerializer(serializers.Serializer):
    name = serializers.CharField()
    sku = serializers.CharField()
    stock_quantity = serializers.IntegerField()
    low_stock_threshold = serializers.IntegerField()


class AssistantDigestSerializer(serializers.Serializer):
    stale_unpaid_orders = DigestOrderRowSerializer(many=True)
    low_stock_products = DigestProductRowSerializer(many=True)
