from unittest.mock import patch

from rest_framework import status

from apps.assistant.llm import LLMResponse, ToolCall
from apps.assistant.models import AssistantAction, AssistantMessage
from apps.assistant.tests.base import AssistantTestCase
from apps.orders.models import Order


class RunTurnTests(AssistantTestCase):
    @patch("apps.assistant.services.send_turn")
    def test_message_creates_draft_order_inline(self, mock_send):
        mock_send.side_effect = [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        call_id="call_1",
                        name="create_draft_order",
                        arguments={
                            "customer": {"name": "New Customer", "email": "new@example.com"},
                            "lines": [{"sku": self.product.sku, "quantity": 2}],
                            "source_message": "2 black hoodies please",
                        },
                    )
                ]
            ),
            LLMResponse(content="I've drafted the order for you — take a look."),
        ]
        response = self.client.post(
            "/api/v1/assistant/messages/", {"message": "2 black hoodies please"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["created_orders"]), 1)
        self.assertEqual(response.data["created_orders"][0]["source_message"], "2 black hoodies please")
        self.assertIn("drafted", response.data["reply"])

        order = Order.objects.get(pk=response.data["created_orders"][0]["id"])
        self.assertEqual(order.store_id, self.store.id)

        # Tool calls/results persisted so the next turn can reconstruct the conversation.
        self.assertTrue(
            AssistantMessage.objects.filter(
                conversation__store=self.store, item_type=AssistantMessage.ItemType.FUNCTION_CALL
            ).exists()
        )

    @patch("apps.assistant.services.send_turn")
    @patch("apps.payments.services.paypal_client.create_order")
    def test_order_card_persists_and_a_later_checkout_does_not_retrigger_it(
        self, mock_paypal_create, mock_send
    ):
        mock_paypal_create.return_value = {
            "id": "PAYPAL-ORDER-1",
            "status": "CREATED",
            "approve_url": "https://sandbox.paypal.com/x",
            "raw": {},
        }
        mock_send.side_effect = [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        call_id="call_1",
                        name="create_draft_order",
                        arguments={
                            "customer": {"name": "Ayesha Nazir"},
                            "lines": [{"sku": self.product.sku, "quantity": 1}],
                        },
                    )
                ]
            ),
            LLMResponse(content="Created the draft order."),
        ]
        created = self.client.post(
            "/api/v1/assistant/messages/", {"message": "order for Ayesha"}, format="json"
        )
        conversation_id = created.data["conversation_id"]
        order_id = created.data["created_orders"][0]["id"]
        order = Order.objects.get(pk=order_id)
        order.fulfilment_status = Order.FulfilmentStatus.UNFULFILLED
        order.payment_status = Order.PaymentStatus.UNPAID
        order.save(update_fields=["fulfilment_status", "payment_status"])

        # A later, unrelated turn that just creates a checkout for the SAME order — this
        # must not look like a second order was created.
        mock_send.side_effect = [
            LLMResponse(
                tool_calls=[
                    ToolCall(call_id="call_2", name="create_checkout", arguments={"order_id": order_id})
                ]
            ),
            LLMResponse(content="Sent her a payment link."),
        ]
        followup = self.client.post(
            "/api/v1/assistant/messages/",
            {"message": "request payment from her", "conversation_id": conversation_id},
            format="json",
        )
        self.assertEqual(followup.data["created_orders"], [])

        detail = self.client.get(f"/api/v1/assistant/conversations/{conversation_id}/")
        self.assertEqual(
            [o["id"] for o in detail.data["orders"]],
            [order_id],
            "the order card must appear exactly once, anchored to its creating turn",
        )

    @patch("apps.assistant.services.send_turn")
    def test_order_confirmed_by_button_shows_as_confirmed_in_the_next_turn(self, mock_send):
        # The reported bug: the seller confirmed the draft with the card's button (outside the
        # chat), but the model kept calling it a draft — it only had its own stale history.
        mock_send.side_effect = [
            LLMResponse(
                tool_calls=[
                    ToolCall(
                        call_id="call_1",
                        name="create_draft_order",
                        arguments={
                            "customer": {"name": "Ayesha Khan"},
                            "lines": [{"product": self.product.sku, "quantity": 1}],
                        },
                    )
                ]
            ),
            LLMResponse(content="Draft order created."),
        ]
        created = self.client.post(
            "/api/v1/assistant/messages/", {"message": "order for Ayesha"}, format="json"
        )
        conversation_id = created.data["conversation_id"]
        order = Order.objects.get(pk=created.data["created_orders"][0]["id"])

        confirmed = self.client.post(f"/api/v1/orders/{order.id}/confirm/", {}, format="json")
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK)

        mock_send.side_effect = [LLMResponse(content="ok")]
        self.client.post(
            "/api/v1/assistant/messages/",
            {"message": "request payment from her", "conversation_id": conversation_id},
            format="json",
        )
        instructions = mock_send.call_args.kwargs["system_prompt"]
        self.assertIn(f"{order.number} (order_id {order.id})", instructions)
        self.assertIn('fulfilment "unfulfilled" (confirmed — NOT a draft)', instructions)
        self.assertNotIn('fulfilment "draft"', instructions)

        # And the stale snapshot from the earlier turn is no longer sent at all.
        input_items = mock_send.call_args.kwargs["input_items"]
        self.assertFalse(any(item.get("type") == "function_call_output" for item in input_items))
        self.assertEqual(input_items[-1], {"role": "user", "content": "request payment from her"})

    @patch("apps.assistant.services.send_turn")
    def test_current_turn_tool_results_are_still_sent(self, mock_send):
        mock_send.side_effect = [
            LLMResponse(tool_calls=[ToolCall(call_id="c1", name="find_products", arguments={"query": "hoodie"})]),
            LLMResponse(content="Found it."),
        ]
        self.client.post("/api/v1/assistant/messages/", {"message": "do I have hoodies"}, format="json")
        second_round_items = mock_send.call_args_list[1].kwargs["input_items"]
        self.assertTrue(
            any(item.get("type") == "function_call_output" for item in second_round_items),
            "the model must still see what it looked up in the turn it is answering",
        )

    @patch("apps.assistant.services.send_turn")
    def test_message_surfaces_pending_action(self, mock_send):
        order_id = self.paid_order()
        mock_send.side_effect = [
            LLMResponse(
                tool_calls=[
                    ToolCall(call_id="call_1", name="propose_refund", arguments={"order_id": order_id})
                ]
            ),
            LLMResponse(content="I've proposed a refund — confirm it when you're ready."),
        ]
        response = self.client.post(
            "/api/v1/assistant/messages/", {"message": "refund that order"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["pending_actions"]), 1)
        self.assertEqual(response.data["pending_actions"][0]["action_type"], "refund")
        self.assertEqual(response.data["pending_actions"][0]["status"], "pending")
        self.assertTrue(AssistantAction.objects.filter(order_id=order_id, status="pending").exists())

    @patch("apps.assistant.services.send_turn")
    def test_runaway_tool_loop_stays_graceful(self, mock_send):
        mock_send.return_value = LLMResponse(
            tool_calls=[ToolCall(call_id="c", name="list_recent_orders", arguments={})]
        )
        response = self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["reply"])

    @patch("apps.assistant.services.send_turn")
    def test_llm_failure_closes_the_turn_with_a_reply_instead_of_a_bare_500(self, mock_send):
        from apps.common.exceptions import BadGatewayError

        mock_send.side_effect = BadGatewayError("Orbiz AI could not process that message.")
        response = self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")
        # The whole point: this still comes back 200, like any other successful send, so the
        # seller's message was never silently orphaned with no visible reply.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reply"], "Orbiz AI could not process that message.")

        conversation_id = response.data["conversation_id"]
        detail = self.client.get(f"/api/v1/assistant/conversations/{conversation_id}/")
        messages = detail.data["messages"]
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["content"], "Orbiz AI could not process that message.")

    @patch("apps.assistant.services.send_turn")
    def test_unexpected_llm_crash_still_closes_the_turn_gracefully(self, mock_send):
        mock_send.side_effect = RuntimeError("boom")
        response = self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("went wrong", response.data["reply"])

    def test_other_users_conversation_list_is_isolated(self):
        with patch("apps.assistant.services.send_turn") as mock_send:
            mock_send.return_value = LLMResponse(content="hi there")
            self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")

        self.client.force_authenticate(self.other)
        response = self.client.get("/api/v1/assistant/conversations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    @patch("apps.assistant.services.send_turn")
    def test_sending_without_conversation_id_starts_a_new_one(self, mock_send):
        mock_send.return_value = LLMResponse(content="ok")
        first = self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")
        second = self.client.post("/api/v1/assistant/messages/", {"message": "hi again"}, format="json")
        self.assertNotEqual(first.data["conversation_id"], second.data["conversation_id"])

    @patch("apps.assistant.services.send_turn")
    def test_sending_with_conversation_id_continues_it(self, mock_send):
        mock_send.return_value = LLMResponse(content="ok")
        first = self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")
        second = self.client.post(
            "/api/v1/assistant/messages/",
            {"message": "follow up", "conversation_id": first.data["conversation_id"]},
            format="json",
        )
        self.assertEqual(first.data["conversation_id"], second.data["conversation_id"])

    def test_conversation_list_and_detail(self):
        with patch("apps.assistant.services.send_turn") as mock_send:
            mock_send.return_value = LLMResponse(content="Sure, here you go.")
            created = self.client.post(
                "/api/v1/assistant/messages/", {"message": "how many orders unpaid"}, format="json"
            )
        conversation_id = created.data["conversation_id"]

        listing = self.client.get("/api/v1/assistant/conversations/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 1)
        self.assertIn("how many orders unpaid", listing.data["results"][0]["preview"])

        detail = self.client.get(f"/api/v1/assistant/conversations/{conversation_id}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(len(detail.data["messages"]), 2)

    def test_create_conversation_endpoint(self):
        response = self.client.post("/api/v1/assistant/conversations/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["messages"], [])

    def test_cannot_message_another_stores_conversation(self):
        with patch("apps.assistant.services.send_turn") as mock_send:
            mock_send.return_value = LLMResponse(content="ok")
            created = self.client.post("/api/v1/assistant/messages/", {"message": "hi"}, format="json")

        self.client.force_authenticate(self.other)
        response = self.client.post(
            "/api/v1/assistant/messages/",
            {"message": "hijack", "conversation_id": created.data["conversation_id"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
