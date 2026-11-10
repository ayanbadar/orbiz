"""Server-side Channel3 client. Key never leaves the backend."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class Channel3Error(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class Channel3NotConfigured(Channel3Error):
    pass


def _api_key() -> str:
    key = getattr(settings, "CHANNEL3_API_KEY", "") or ""
    if not key:
        raise Channel3NotConfigured("Channel3 is not configured (CHANNEL3_API_KEY).")
    return key


def _base_url() -> str:
    return getattr(settings, "CHANNEL3_BASE_URL", "https://api.trychannel3.com").rstrip("/")


def _pick_offer(product: dict[str, Any]) -> dict[str, Any] | None:
    offers = product.get("offers") or []
    if not offers:
        return None
    in_stock = [o for o in offers if (o.get("availability") or "") == "InStock"]
    pool = in_stock or offers

    def price_value(offer: dict) -> Decimal:
        price = offer.get("price") or {}
        raw = price.get("price") if "price" in price else price.get("amount")
        try:
            return Decimal(str(raw))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("999999")

    return min(pool, key=price_value)


def map_channel3_product(product: dict[str, Any]) -> dict[str, Any]:
    offer = _pick_offer(product)
    price_obj = (offer or {}).get("price") or {}
    suggested = price_obj.get("price") if "price" in price_obj else price_obj.get("amount")
    currency = price_obj.get("currency") or "USD"
    images = product.get("images") or []
    image_url = ""
    if images:
        first = images[0]
        image_url = first if isinstance(first, str) else (first.get("url") or "")
    brands = product.get("brands") or []
    brand = brands[0].get("name") if brands and isinstance(brands[0], dict) else None
    return {
        "channel3_product_id": product.get("id") or "",
        "title": product.get("title") or "",
        "description": product.get("description") or "",
        "image_url": image_url,
        "suggested_price": str(suggested) if suggested is not None else None,
        "currency": currency,
        "brand": brand,
        "availability": (offer or {}).get("availability"),
    }


def search_products(*, query: str, limit: int = 10, page_token: str | None = None) -> dict[str, Any]:
    key = _api_key()
    body: dict[str, Any] = {"limit": min(max(limit, 1), 30)}
    if page_token:
        body["page_token"] = page_token
        body["query"] = query
    else:
        body["query"] = query

    url = f"{_base_url()}/v1/search"
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                url,
                headers={"x-api-key": key, "Content-Type": "application/json"},
                json=body,
            )
    except httpx.HTTPError as exc:
        logger.warning("Channel3 search request failed: %s", exc)
        raise Channel3Error("Channel3 is unreachable right now.") from exc

    if response.status_code >= 400:
        logger.warning("Channel3 search HTTP %s: %s", response.status_code, response.text[:200])
        raise Channel3Error(
            "Channel3 search failed.",
            status_code=response.status_code,
        )

    data = response.json()
    products = data.get("products") or []
    return {
        "results": [map_channel3_product(p) for p in products],
        "next_page_token": data.get("next_page_token"),
    }


def retrieve_product(channel3_product_id: str) -> dict[str, Any]:
    key = _api_key()
    url = f"{_base_url()}/v1/products/{channel3_product_id}"
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(url, headers={"x-api-key": key})
    except httpx.HTTPError as exc:
        logger.warning("Channel3 retrieve failed: %s", exc)
        raise Channel3Error("Channel3 is unreachable right now.") from exc

    if response.status_code == 404:
        raise Channel3Error("Channel3 product not found.", status_code=404)
    if response.status_code >= 400:
        raise Channel3Error("Channel3 product lookup failed.", status_code=response.status_code)

    return map_channel3_product(response.json())
