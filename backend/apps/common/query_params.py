"""Tolerant query-string parsing for store-scoped list endpoints.

Bad input from a URL is ignored (returns None / the default) rather than raising,
so a mistyped filter never turns a list request into a 500.
"""

from collections.abc import Collection
from decimal import Decimal, InvalidOperation


def parse_int(raw: str | None) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def parse_decimal(raw: str | None) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, TypeError):
        return None


def resolve_ordering(raw: str | None, *, allowed: Collection[str], default: str) -> str:
    """Return `raw` when it is an allowed ordering key, else `default`."""
    return raw if raw in allowed else default
