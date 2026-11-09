"""Server-side OpenAI Responses API client. Key never leaves the backend."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx
from django.conf import settings

from apps.common.exceptions import BadGatewayError, ServiceUnavailableError

logger = logging.getLogger(__name__)


class AssistantNotConfigured(ServiceUnavailableError):
    default_code = "assistant_not_configured"


@dataclass
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Normalized reply: the model's text (if any) and any tool calls it wants run."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


def is_configured() -> bool:
    return bool(getattr(settings, "OPENAI_API_KEY", "") or "")


def _api_key() -> str:
    key = getattr(settings, "OPENAI_API_KEY", "") or ""
    if not key:
        raise AssistantNotConfigured("Orbiz AI is not configured (OPENAI_API_KEY).")
    return key


def _base_url() -> str:
    return getattr(settings, "OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")


def _model() -> str:
    return getattr(settings, "ASSISTANT_MODEL", "gpt-5-mini")


def _reasoning_effort() -> str:
    # GPT-5-family models reason by default even to pick a tool, which is most of what this
    # agent's turns are — that cost ~13-15s per round at the default "medium" effort in testing.
    # "low" keeps enough reasoning for correct tool choice (unlike "minimal", which trades
    # tool-call accuracy for speed) while cutting that per-round latency noticeably. Empty/unset
    # settings values and non GPT-5-family models (no "reasoning" support) fall back to leaving
    # the field off the request entirely.
    return getattr(settings, "ASSISTANT_REASONING_EFFORT", "low") or ""


def send_turn(
    *,
    system_prompt: str,
    input_items: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> LLMResponse:
    """
    One Responses API call. `input_items` are prior `message` / `function_call` /
    `function_call_output` items in order; the caller owns conversation reconstruction.
    """
    key = _api_key()
    body: dict[str, Any] = {
        "model": _model(),
        "instructions": system_prompt,
        "input": input_items,
        "tools": tools,
    }
    effort = _reasoning_effort()
    if effort:
        body["reasoning"] = {"effort": effort}
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{_base_url()}/responses",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=body,
            )
    except httpx.HTTPError as exc:
        logger.warning("Orbiz AI request failed: %s", exc)
        raise BadGatewayError("Orbiz AI is unreachable right now.") from exc

    if response.status_code >= 400:
        logger.warning("Orbiz AI HTTP %s: %s", response.status_code, response.text[:500])
        raise BadGatewayError(
            "Orbiz AI could not process that message.",
            extra={"status_code": response.status_code},
        )

    data = response.json()
    return _parse_response(data)


def _parse_response(data: dict[str, Any]) -> LLMResponse:
    content_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for item in data.get("output") or []:
        item_type = item.get("type")
        if item_type == "message":
            for part in item.get("content") or []:
                if part.get("type") == "output_text" and part.get("text"):
                    content_parts.append(part["text"])
        elif item_type == "function_call":
            import json as _json

            try:
                arguments = _json.loads(item.get("arguments") or "{}")
            except ValueError:
                arguments = {}
            tool_calls.append(
                ToolCall(
                    call_id=item.get("call_id") or "",
                    name=item.get("name") or "",
                    arguments=arguments,
                )
            )
    return LLMResponse(content="\n".join(content_parts), tool_calls=tool_calls)
