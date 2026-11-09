"""
Orbiz AI's move to the multi-tenancy permission model (§2 of the plan): a non-admin teammate
with the right Role can use it, one without it cannot, and conversations are shared at the
store level rather than siloed per user.
"""

from unittest.mock import patch

from rest_framework import status

from apps.accounts.models import User
from apps.assistant.llm import LLMResponse
from apps.assistant.models import AssistantConversation
from apps.assistant.tests.base import PASSWORD, AssistantTestCase
from apps.orders.models import Order
from apps.stores.models import Role, StoreMembership


class AssistantPermissionTests(AssistantTestCase):
    def test_teammate_without_assistant_permission_is_forbidden(self):
        no_access_role = Role.objects.create(store=self.store, name="Sales", permissions=["orders.read"])
        outsider = User.objects.create_user(email="outsider@example.com", password=PASSWORD, first_name="O")
        StoreMembership.objects.create(store=self.store, user=outsider, role=no_access_role)
        self.client.force_authenticate(outsider)

        response = self.client.get("/api/v1/assistant/digest/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teammate_with_assistant_permission_can_use_it(self):
        self.client.force_authenticate(self.teammate)
        response = self.client.get("/api/v1/assistant/digest/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with patch("apps.assistant.services.send_turn") as mock_send:
            mock_send.return_value = LLMResponse(content="hi there")
            response = self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_teammate_without_update_permission_cannot_confirm_an_action(self):
        from apps.assistant.models import AssistantAction

        # Order created as the store admin — this test is about the *confirm* permission, not
        # whether the teammate can also create orders.
        order_id = self.confirmed_order()
        action = AssistantAction.objects.create(
            store=self.store, order_id=order_id, action_type=AssistantAction.ActionType.REFUND, payload={}
        )

        read_only_role = Role.objects.create(
            store=self.store, name="Read only", permissions=["assistant.read", "assistant.create"]
        )
        self.teammate.membership.role = read_only_role
        self.teammate.membership.save(update_fields=["role"])
        self.client.force_authenticate(self.teammate)

        response = self.client.post(f"/api/v1/assistant/actions/{action.id}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_store_admin_keeps_full_access_without_an_explicit_role(self):
        # self.user is a store admin with no Role row at all — membership.is_store_admin alone
        # must still satisfy the new assistant.* gate, same as every other resource.
        response = self.client.get("/api/v1/assistant/digest/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ConversationSharingTests(AssistantTestCase):
    def test_a_teammate_in_the_same_store_sees_and_can_continue_the_conversation(self):
        with patch("apps.assistant.services.send_turn") as mock_send:
            mock_send.return_value = LLMResponse(content="hi there")
            created = self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")
        conversation_id = created.data["conversation_id"]

        self.client.force_authenticate(self.teammate)
        listing = self.client.get("/api/v1/assistant/conversations/")
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["results"][0]["id"], conversation_id)

        with patch("apps.assistant.services.send_turn") as mock_send:
            mock_send.return_value = LLMResponse(content="still here")
            reply = self.client.post(
                "/api/v1/assistant/messages/",
                {"message": "follow up", "conversation_id": conversation_id},
                format="json",
            )
        self.assertEqual(reply.status_code, status.HTTP_200_OK)
        self.assertEqual(reply.data["conversation_id"], conversation_id)
        self.assertEqual(
            AssistantConversation.objects.get(pk=conversation_id).messages.count(), 4
        )


class ConversationDeleteTests(AssistantTestCase):
    def test_delete_removes_conversation_and_messages(self):
        with patch("apps.assistant.services.send_turn") as mock_send:
            mock_send.return_value = LLMResponse(content="hi there")
            created = self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")
        conversation_id = created.data["conversation_id"]

        response = self.client.delete(f"/api/v1/assistant/conversations/{conversation_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AssistantConversation.objects.filter(pk=conversation_id).exists())

    def test_delete_detaches_but_never_deletes_a_pending_action_or_its_order(self):
        from apps.assistant.models import AssistantAction
        from apps.orders.models import Order

        order_id = self.confirmed_order()
        conversation = AssistantConversation.objects.create(store=self.store, created_by=self.user)
        action = AssistantAction.objects.create(
            store=self.store,
            conversation=conversation,
            order_id=order_id,
            action_type=AssistantAction.ActionType.REFUND,
            payload={},
        )

        response = self.client.delete(f"/api/v1/assistant/conversations/{conversation.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        action.refresh_from_db()
        self.assertIsNone(action.conversation_id)
        self.assertEqual(action.status, AssistantAction.Status.PENDING)
        self.assertTrue(Order.objects.filter(pk=order_id).exists())

    def test_cannot_delete_another_stores_conversation(self):
        other_conversation = AssistantConversation.objects.create(
            store=self.other_store, created_by=self.other
        )
        response = self.client.delete(f"/api/v1/assistant/conversations/{other_conversation.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(AssistantConversation.objects.filter(pk=other_conversation.id).exists())

    def test_teammate_without_delete_permission_is_forbidden(self):
        self.client.force_authenticate(self.teammate)  # has read/create/update, not delete
        conversation = AssistantConversation.objects.create(store=self.store, created_by=self.user)
        response = self.client.delete(f"/api/v1/assistant/conversations/{conversation.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SourceRecordsTests(AssistantTestCase):
    def test_assistant_reply_carries_the_order_it_looked_up(self):
        order_id = self.confirmed_order()
        order_number = self.client.get(f"/api/v1/orders/{order_id}/").data["number"]

        with patch("apps.assistant.services.send_turn") as mock_send:
            from apps.assistant.llm import ToolCall

            mock_send.side_effect = [
                LLMResponse(
                    tool_calls=[
                        ToolCall(call_id="call_1", name="get_order", arguments={"order_number": order_number})
                    ]
                ),
                LLMResponse(content=f"{order_number} is confirmed and unpaid."),
            ]
            self.client.post("/api/v1/assistant/messages/", {"message": "status of my order"}, format="json")

        detail = self.client.get("/api/v1/assistant/conversations/")
        conversation_id = detail.data["results"][0]["id"]
        full = self.client.get(f"/api/v1/assistant/conversations/{conversation_id}/")
        assistant_messages = [m for m in full.data["messages"] if m["role"] == "assistant"]
        self.assertEqual(len(assistant_messages), 1)
        self.assertIn(order_number, assistant_messages[0]["source_records"])

    def test_list_recent_orders_result_table_carries_date_range_into_view_all(self):
        order_id = self.confirmed_order()
        Order.objects.filter(pk=order_id).update(created_at="2026-11-03T12:00:00Z")

        with patch("apps.assistant.services.send_turn") as mock_send:
            from apps.assistant.llm import ToolCall

            mock_send.side_effect = [
                LLMResponse(
                    tool_calls=[
                        ToolCall(
                            call_id="call_1",
                            name="list_recent_orders",
                            arguments={"created_after": "2026-11-01", "created_before": "2026-11-07"},
                        )
                    ]
                ),
                LLMResponse(content="Found orders in that range."),
            ]
            self.client.post(
                "/api/v1/assistant/messages/", {"message": "orders between nov 1 and nov 7"}, format="json"
            )

        conversation_id = self.client.get("/api/v1/assistant/conversations/").data["results"][0]["id"]
        full = self.client.get(f"/api/v1/assistant/conversations/{conversation_id}/")
        assistant_messages = [m for m in full.data["messages"] if m["role"] == "assistant"]
        tables = assistant_messages[0]["result_tables"]
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["kind"], "orders")
        self.assertEqual(
            tables[0]["view_all"], {"created_after": "2026-11-01", "created_before": "2026-11-07"}
        )

    def test_user_message_never_carries_source_records(self):
        with patch("apps.assistant.services.send_turn") as mock_send:
            mock_send.return_value = LLMResponse(content="ok")
            self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")

        conversation_id = self.client.get("/api/v1/assistant/conversations/").data["results"][0]["id"]
        full = self.client.get(f"/api/v1/assistant/conversations/{conversation_id}/")
        user_messages = [m for m in full.data["messages"] if m["role"] == "user"]
        self.assertEqual(user_messages[0]["source_records"], [])
