"""Server-side PayPal Orders API v2 client. Credentials never leave the backend."""

from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Any

import httpx
from django.conf import settings

from apps.common.exceptions import BadGatewayError, ServiceUnavailableError

logger = logging.getLogger(__name__)

_token_cache: dict[str, Any] = {"access_token": "", "expires_at": 0.0}


class PayPalNotConfigured(ServiceUnavailableError):
    default_code = "paypal_not_configured"


def is_sandbox_mode() -> bool:
    mode = (getattr(settings, "PAYPAL_MODE", "sandbox") or "sandbox").lower()
    return mode != "live"


def is_configured() -> bool:
    return bool(
        (getattr(settings, "PAYPAL_CLIENT_ID", "") or "").strip()
        and (getattr(settings, "PAYPAL_CLIENT_SECRET", "") or "").strip()
    )


def _require_configured() -> None:
    if not is_configured():
        raise PayPalNotConfigured(
            "PayPal is not configured (PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET)."
        )


def _api_base() -> str:
    override = (getattr(settings, "PAYPAL_API_BASE", "") or "").strip().rstrip("/")
    if override:
        return override
    if is_sandbox_mode():
        return "https://api-m.sandbox.paypal.com"
    return "https://api-m.paypal.com"


def _get_access_token() -> str:
    _require_configured()
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 30:
        return _token_cache["access_token"]

    client_id = settings.PAYPAL_CLIENT_ID
    client_secret = settings.PAYPAL_CLIENT_SECRET
    url = f"{_api_base()}/v1/oauth2/token"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                headers={"Accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        logger.warning("PayPal OAuth transport error: %s", type(exc).__name__)
        raise BadGatewayError("PayPal authentication request failed.") from exc

    if response.status_code >= 500:
        raise BadGatewayError("PayPal authentication is temporarily unavailable.")
    if response.status_code >= 400:
        logger.warning("PayPal OAuth rejected status=%s", response.status_code)
        raise BadGatewayError("PayPal rejected authentication credentials.")

    data = response.json()
    token = data.get("access_token") or ""
    expires_in = int(data.get("expires_in") or 300)
    if not token:
        raise BadGatewayError("PayPal authentication returned no access token.")
    _token_cache["access_token"] = token
    _token_cache["expires_at"] = now + expires_in
    return token


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _require_configured()
    url = f"{_api_base()}{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method,
                url,
                headers=_auth_headers(),
                json=json_body,
            )
    except httpx.HTTPError as exc:
        logger.warning("PayPal %s %s transport error: %s", method, path, type(exc).__name__)
        raise BadGatewayError("PayPal request failed.") from exc

    if response.status_code >= 500:
        raise BadGatewayError("PayPal is temporarily unavailable.")
    if response.status_code >= 400:
        detail = ""
        try:
            payload = response.json()
            detail = payload.get("message") or payload.get("name") or ""
        except Exception:
            detail = ""
        logger.warning(
            "PayPal %s %s rejected status=%s detail=%s",
            method,
            path,
            response.status_code,
            detail or "(none)",
        )
        message = "PayPal rejected the payment request."
        if detail:
            message = f"{message} {detail}"
        raise BadGatewayError(message)

    if response.status_code == 204 or not response.content:
        return {}
    return response.json()


def _approve_url(order_payload: dict[str, Any]) -> str:
    for link in order_payload.get("links") or []:
        if (link.get("rel") or "") == "approve":
            return link.get("href") or ""
    return ""


def create_order(
    *,
    amount: Decimal,
    currency: str,
    return_url: str,
    cancel_url: str,
    custom_id: str,
    reference_id: str,
) -> dict[str, Any]:
    """
    Create a PayPal order with intent CAPTURE.

    Returns dict with keys: id, status, approve_url, raw.
    """
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": reference_id[:127],
                "custom_id": custom_id[:127],
                "amount": {
                    "currency_code": currency.upper(),
                    "value": f"{amount.quantize(Decimal('0.01'))}",
                },
            }
        ],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "PAY_NOW",
            "shipping_preference": "NO_SHIPPING",
        },
    }
    raw = _request("POST", "/v2/checkout/orders", json_body=body)
    order_id = raw.get("id") or ""
    if not order_id:
        raise BadGatewayError("PayPal create order returned no id.")
    return {
        "id": order_id,
        "status": raw.get("status") or "",
        "approve_url": _approve_url(raw),
        "raw": raw,
    }


def capture_order(*, paypal_order_id: str) -> dict[str, Any]:
    """Capture an approved PayPal order. Returns capture summary + raw."""
    raw = _request("POST", f"/v2/checkout/orders/{paypal_order_id}/capture", json_body={})
    capture_id = ""
    capture_status = ""
    for unit in raw.get("purchase_units") or []:
        payments = unit.get("payments") or {}
        for capture in payments.get("captures") or []:
            capture_id = capture.get("id") or capture_id
            capture_status = capture.get("status") or capture_status
            if capture_id:
                break
        if capture_id:
            break
    return {
        "id": raw.get("id") or paypal_order_id,
        "status": raw.get("status") or "",
        "capture_id": capture_id,
        "capture_status": capture_status,
        "raw": raw,
    }


def verify_webhook(*, headers: dict[str, str], body: bytes | str) -> bool:
    """
    Verify webhook authenticity via PayPal verify-webhook-signature.

    Returns True when verification_status is SUCCESS.
    """
    _require_configured()
    webhook_id = (getattr(settings, "PAYPAL_WEBHOOK_ID", "") or "").strip()
    if not webhook_id:
        raise PayPalNotConfigured("PayPal webhook is not configured (PAYPAL_WEBHOOK_ID).")

    if isinstance(body, bytes):
        body_text = body.decode("utf-8")
    else:
        body_text = body

    import json

    try:
        webhook_event = json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise BadGatewayError("PayPal webhook body is not valid JSON.") from exc

    transmission_id = headers.get("PAYPAL-TRANSMISSION-ID") or headers.get(
        "Paypal-Transmission-Id", ""
    )
    transmission_time = headers.get("PAYPAL-TRANSMISSION-TIME") or headers.get(
        "Paypal-Transmission-Time", ""
    )
    transmission_sig = headers.get("PAYPAL-TRANSMISSION-SIG") or headers.get(
        "Paypal-Transmission-Sig", ""
    )
    cert_url = headers.get("PAYPAL-CERT-URL") or headers.get("Paypal-Cert-Url", "")
    auth_algo = headers.get("PAYPAL-AUTH-ALGO") or headers.get("Paypal-Auth-Algo", "")

    payload = {
        "transmission_id": transmission_id,
        "transmission_time": transmission_time,
        "cert_url": cert_url,
        "auth_algo": auth_algo,
        "transmission_sig": transmission_sig,
        "webhook_id": webhook_id,
        "webhook_event": webhook_event,
    }
    result = _request("POST", "/v1/notifications/verify-webhook-signature", json_body=payload)
    return (result.get("verification_status") or "").upper() == "SUCCESS"


def clear_token_cache() -> None:
    """Test helper."""
    _token_cache["access_token"] = ""
    _token_cache["expires_at"] = 0.0
