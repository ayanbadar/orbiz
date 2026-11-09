"""
llm.py's request-shaping, verified against a mocked httpx.Client.post — no real OpenAI call is
ever made here, in line with the project rule to never hit OpenAI from a test or an agent
session.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from apps.assistant import llm
from apps.common.exceptions import BadGatewayError, TooManyRequestsError


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


@override_settings(OPENAI_API_KEY="test-key", ASSISTANT_MODEL="gpt-5-mini")
class RequestShapeTests(TestCase):
    @patch("httpx.Client.post")
    def test_parallel_tool_calls_is_disabled_to_match_strict_mode(self, mock_post):
        mock_post.return_value = _mock_response()
        llm.send_turn(system_prompt="hi", input_items=[], tools=[])
        sent_body = mock_post.call_args.kwargs["json"]
        self.assertIs(sent_body["parallel_tool_calls"], False)


@override_settings(OPENAI_API_KEY="test-key", ASSISTANT_MODEL="gpt-5-mini")
class ErrorHandlingTests(TestCase):
    """A seller-facing message for each failure mode, never an unhandled 500 mid-turn."""

    @patch("httpx.Client.post")
    def test_429_raises_a_distinct_rate_limited_error_not_a_generic_bad_gateway(self, mock_post):
        resp = MagicMock()
        resp.status_code = 429
        resp.text = "rate limited"
        mock_post.return_value = resp
        with self.assertRaises(TooManyRequestsError) as caught:
            llm.send_turn(system_prompt="hi", input_items=[], tools=[])
        self.assertEqual(caught.exception.status_code, 429)

    @patch("httpx.Client.post")
    def test_other_4xx_still_raises_bad_gateway(self, mock_post):
        resp = MagicMock()
        resp.status_code = 400
        resp.text = "bad request"
        mock_post.return_value = resp
        with self.assertRaises(BadGatewayError):
            llm.send_turn(system_prompt="hi", input_items=[], tools=[])

    @patch("httpx.Client.post")
    def test_non_json_body_raises_bad_gateway_not_an_unhandled_exception(self, mock_post):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.side_effect = ValueError("not json")
        resp.text = "<html>not json</html>"
        mock_post.return_value = resp
        with self.assertRaises(BadGatewayError):
            llm.send_turn(system_prompt="hi", input_items=[], tools=[])

    @patch("httpx.Client.post")
    def test_unexpected_json_shape_raises_bad_gateway(self, mock_post):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = ["not", "a", "dict"]
        resp.text = '["not", "a", "dict"]'
        mock_post.return_value = resp
        with self.assertRaises(BadGatewayError):
            llm.send_turn(system_prompt="hi", input_items=[], tools=[])
