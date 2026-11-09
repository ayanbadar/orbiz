"""
llm.py's request-shaping, verified against a mocked httpx.Client.post — no real OpenAI call is
ever made here, in line with the project rule to never hit OpenAI from a test or an agent
session.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.assistant import llm


def _mock_response(output: list | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"output": output or []}
    return resp


@override_settings(OPENAI_API_KEY="test-key", ASSISTANT_MODEL="gpt-5-mini")
class ReasoningEffortTests(TestCase):
    @patch("httpx.Client.post")
    def test_default_effort_is_low_and_reaches_the_request_body(self, mock_post):
        mock_post.return_value = _mock_response()
        llm.send_turn(system_prompt="hi", input_items=[], tools=[])
        sent_body = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_body["reasoning"], {"effort": "low"})

    @override_settings(ASSISTANT_REASONING_EFFORT="minimal")
    @patch("httpx.Client.post")
    def test_effort_is_configurable(self, mock_post):
        mock_post.return_value = _mock_response()
        llm.send_turn(system_prompt="hi", input_items=[], tools=[])
        sent_body = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_body["reasoning"], {"effort": "minimal"})

    @override_settings(ASSISTANT_REASONING_EFFORT="")
    @patch("httpx.Client.post")
    def test_empty_effort_drops_the_field_entirely(self, mock_post):
        mock_post.return_value = _mock_response()
        llm.send_turn(system_prompt="hi", input_items=[], tools=[])
        sent_body = mock_post.call_args.kwargs["json"]
        self.assertNotIn("reasoning", sent_body)
