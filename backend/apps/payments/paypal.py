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


ORDER_ALREADY_CAPTURED = "ORDER_ALREADY_CAPTURED"
ORDER_NOT_APPROVED = "ORDER_NOT_APPROVED"

# PayPal `details[].issue` codes → seller-readable messages.
_ISSUE_MESSAGES: dict[str, str] = {
    ORDER_NOT_APPROVED: (
        "The buyer hasn't approved this payment on PayPal yet. Send them the link and "
        "capture once they have approved it."
    ),
    "REFUND_AMOUNT_EXCEEDED": "That is more than is left to refund on this payment.",
    "CAPTURE_FULLY_REFUNDED": "This payment has already been fully refunded.",
    "REFUND_TIME_LIMIT_EXCEEDED": "PayPal only allows refunds within 180 days of the payment.",
    "REFUND_NOT_ALLOWED_AFTER_180_DAYS": "PayPal only allows refunds within 180 days of the payment.",
    "REFUND_NOT_ALLOWED": "PayPal does not allow this payment to be refunded.",
    "PARTIAL_REFUND_NOT_ALLOWED": "PayPal only allows a full refund for this payment.",
    "MAX_NUMBER_OF_REFUNDS_EXCEEDED": "PayPal's refund limit for this payment was reached.",
    "PENDING_CAPTURE": "This payment is still pending — refund it once it clears.",
    "REFUND_FAILED_INSUFFICIENT_FUNDS": "The PayPal merchant balance is too low for this refund.",
    "TRANSACTION_DISPUTED": "This payment is under dispute and cannot be partially refunded.",
    "REFUND_NOT_PERMITTED_DUE_TO_CHARGEBACK": "A chargeback on this payment blocks the refund.",
    "CURRENCY_NOT_SUPPORTED": "PayPal does not support this currency for the merchant account.",
    "PERMISSION_DENIED": (
        "PayPal denied the request. Enable Invoicing for the Sandbox app "
        "(Developer Dashboard → App → Features)."
    ),
}


def _parse_error(response: httpx.Response) -> tuple[str, str]:
    """Return (message, issue) from a PayPal error body; either may be empty."""
    try:
        payload = response.json()
    except ValueError:
        return "", ""
    if not isinstance(payload, dict):
        return "", ""
    details = payload.get("details")
    issue = ""
    if isinstance(details, list) and details and isinstance(details[0], dict):
        issue = str(details[0].get("issue") or "")
    return str(payload.get("message") or payload.get("name") or ""), issue


def _request(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    _require_configured()
    url = f"{_api_base()}{path}"
    request_headers = {**_auth_headers(), **(headers or {})}
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                method,
                url,
                headers=request_headers,
                json=json_body,
            )
    except httpx.HTTPError as exc:
        logger.warning("PayPal %s %s transport error: %s", method, path, type(exc).__name__)
        raise BadGatewayError("PayPal request failed.") from exc

    if response.status_code >= 500:
        raise BadGatewayError("PayPal is temporarily unavailable.")
    if response.status_code >= 400:
        detail, issue = _parse_error(response)
        logger.warning(
            "PayPal %s %s rejected status=%s issue=%s detail=%s",
            method,
            path,
            response.status_code,
            issue or "(none)",
            detail or "(none)",
        )
        message = _ISSUE_MESSAGES.get(issue)
        if message is None:
            message = "PayPal rejected the payment request."
            if detail:
                message = f"{message} {detail}"
        raise BadGatewayError(message, extra={"paypal_issue": issue} if issue else None)

    if response.status_code == 204 or not response.content:
        return {}
    return response.json()


def _approve_url(order_payload: dict[str, Any]) -> str:
    for link in order_payload.get("links") or []:
        if (link.get("rel") or "") == "approve":
            return link.get("href") or ""
    return ""


def _checkout_items(
    *, amount: Decimal, currency: str, items: list[dict[str, Any]] | None
) -> list[dict[str, Any]] | None:
    """
    PayPal `items[]` for the buyer's review page and receipt, or None when they can't be
    sent safely: PayPal needs every price > 0 and `item_total` to equal the order amount.
    """
    if not items or len(items) > 100:
        return None
    code = currency.upper()
    rows: list[dict[str, Any]] = []
    item_total = Decimal("0.00")
    for item in items:
        unit_price = Decimal(item["unit_price"]).quantize(Decimal("0.01"))
        quantity = int(item["quantity"])
        if unit_price <= 0 or quantity < 1:
            return None
        item_total += unit_price * quantity
        row: dict[str, Any] = {
            "name": str(item["name"])[:127],
            "quantity": str(quantity),
            "unit_amount": {"currency_code": code, "value": f"{unit_price}"},
        }
        if item.get("sku"):
            row["sku"] = str(item["sku"])[:127]
        rows.append(row)
    if item_total.quantize(Decimal("0.01")) != amount.quantize(Decimal("0.01")):
        return None
    return rows


def create_order(
    *,
    amount: Decimal,
    currency: str,
    return_url: str,
    cancel_url: str,
    custom_id: str,
    reference_id: str,
    items: list[dict[str, Any]] | None = None,
    description: str = "",
    invoice_id: str = "",
    brand_name: str = "",
) -> dict[str, Any]:
    """
    Create a PayPal order with intent CAPTURE.

    `items` ({name, quantity, unit_price, sku}), `description`, `invoice_id` (shown in the
    buyer's PayPal history and emails; PayPal rejects a repeat per merchant) and
    `brand_name` make the buyer's payment page and receipt say what is being bought and
    from whom. Returns dict with keys: id, status, approve_url, raw.
    """
    code = currency.upper()
    value = f"{amount.quantize(Decimal('0.01'))}"
    unit: dict[str, Any] = {
        "reference_id": reference_id[:127],
        "custom_id": custom_id[:127],
        "amount": {"currency_code": code, "value": value},
    }
    paypal_items = _checkout_items(amount=amount, currency=code, items=items)
    if paypal_items is not None:
        unit["items"] = paypal_items
        unit["amount"]["breakdown"] = {"item_total": {"currency_code": code, "value": value}}
    if description:
        unit["description"] = description[:127]
    if invoice_id:
        unit["invoice_id"] = invoice_id[:127]
    context: dict[str, Any] = {
        "return_url": return_url,
        "cancel_url": cancel_url,
        "user_action": "PAY_NOW",
        "shipping_preference": "NO_SHIPPING",
    }
    if brand_name:
        context["brand_name"] = " ".join(brand_name.split())[:127]
    body = {
        "intent": "CAPTURE",
        "purchase_units": [unit],
        "application_context": context,
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
    return capture_summary(raw, paypal_order_id=paypal_order_id)


def capture_summary(raw: dict[str, Any], *, paypal_order_id: str) -> dict[str, Any]:
    """Summarise a captured order payload (capture response or a fetched order)."""
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


def get_order(*, paypal_order_id: str) -> dict[str, Any]:
    """Fetch a PayPal order (used to settle a capture that already happened)."""
    return _request("GET", f"/v2/checkout/orders/{paypal_order_id}")


def refund_capture(
    *,
    capture_id: str,
    amount: Decimal,
    currency: str,
    note_to_payer: str,
    request_id: str,
) -> dict[str, Any]:
    """
    Refund `amount` of a captured payment.

    `request_id` is sent as PayPal-Request-Id so a retry replays the same refund
    instead of creating a second one. Returns {id, status, raw}.
    """
    body: dict[str, Any] = {
        "amount": {
            "currency_code": currency.upper(),
            "value": f"{amount.quantize(Decimal('0.01'))}",
        }
    }
    if note_to_payer:
        body["note_to_payer"] = note_to_payer[:255]
    raw = _request(
        "POST",
        f"/v2/payments/captures/{capture_id}/refund",
        json_body=body,
        headers={"PayPal-Request-Id": request_id, "Prefer": "return=representation"},
    )
    refund_id = raw.get("id") or ""
    if not refund_id:
        raise BadGatewayError("PayPal refund returned no id.")
    return {"id": refund_id, "status": (raw.get("status") or "").upper(), "raw": raw}


def create_invoice(
    *,
    invoice_number: str,
    reference: str,
    currency: str,
    items: list[dict[str, Any]],
    note: str,
    recipient_email: str,
    recipient_name: str,
    request_id: str,
) -> dict[str, Any]:
    """
    Create a draft PayPal invoice due on receipt. Returns {id, raw}.

    `items` entries are {name, quantity, unit_price}. With no recipient email the
    invoice is still payable by link; nothing is emailed.
    """
    code = currency.upper()
    body: dict[str, Any] = {
        "detail": {
            "currency_code": code,
            "invoice_number": invoice_number,
            "reference": reference[:120],
            "note": note,
            "payment_term": {"term_type": "DUE_ON_RECEIPT"},
        },
        "items": [
            {
                "name": item["name"][:200],
                "quantity": str(item["quantity"]),
                "unit_amount": {
                    "currency_code": code,
                    "value": f"{item['unit_price'].quantize(Decimal('0.01'))}",
                },
                "unit_of_measure": "QUANTITY",
            }
            for item in items
        ],
    }
    if recipient_email:
        given_name, _, surname = recipient_name.strip().partition(" ")
        name: dict[str, str] = {"given_name": given_name or "Customer"}
        if surname.strip():
            name["surname"] = surname.strip()
        body["primary_recipients"] = [
            {"billing_info": {"email_address": recipient_email, "name": name}}
        ]
    raw = _request(
        "POST",
        "/v2/invoicing/invoices",
        json_body=body,
        headers={"PayPal-Request-Id": request_id, "Prefer": "return=representation"},
    )
    invoice_id = raw.get("id") or ""
    if not invoice_id:
        # Without a full representation PayPal returns only a link ending in the id.
        invoice_id = (raw.get("href") or "").rstrip("/").rsplit("/", 1)[-1]
    if not invoice_id:
        raise BadGatewayError("PayPal create invoice returned no id.")
    return {"id": invoice_id, "raw": raw}


def send_invoice(*, invoice_id: str, send_to_recipient: bool) -> None:
    """Move a draft invoice to payable; PayPal emails the recipient when asked to."""
    _request(
        "POST",
        f"/v2/invoicing/invoices/{invoice_id}/send",
        json_body={"send_to_recipient": send_to_recipient, "send_to_invoicer": False},
    )


def get_invoice(*, invoice_id: str) -> dict[str, Any]:
    return _request("GET", f"/v2/invoicing/invoices/{invoice_id}")


def invoice_payer_url(invoice: dict[str, Any]) -> str:
    metadata = (invoice.get("detail") or {}).get("metadata") or {}
    return metadata.get("recipient_view_url") or ""


def invoice_payment_id(invoice: dict[str, Any]) -> str:
    """PayPal payment id of the buyer's payment on an invoice (the refundable capture)."""
    transactions = (invoice.get("payments") or {}).get("transactions") or []
    for transaction in transactions:
        if (transaction.get("type") or "").upper() == "PAYPAL" and transaction.get("payment_id"):
            return str(transaction["payment_id"])
    return ""


def cancel_invoice(*, invoice_id: str) -> None:
    _request(
        "POST",
        f"/v2/invoicing/invoices/{invoice_id}/cancel",
        json_body={"send_to_recipient": False, "send_to_invoicer": False},
    )


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
