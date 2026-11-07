"""Buyer-facing payment emails: rendering only. Delivery goes through apps.notifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from email.utils import formataddr, parseaddr

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import Truncator

from apps.orders.models import Order

REQUEST = "request"
REMINDER = "reminder"

INVOICE_LINK = "invoice"
CHECKOUT_LINK = "checkout"


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text: str
    html: str


def sender_for(store) -> str:
    """`<Store> via Orbiz <configured address>` — the address must stay the authenticated one."""
    _, address = parseaddr(settings.DEFAULT_FROM_EMAIL)
    display = " ".join(f"{store.name} via Orbiz".split())  # no newlines in a header
    return formataddr((display, address))


def _money(currency: str, amount) -> str:
    return f"{currency} {amount:,.2f}"


def _lines(order: Order) -> list[dict]:
    return [
        {
            "name": line.product_name,
            "quantity": line.quantity,
            "unit_price": _money(order.currency, line.unit_price),
            "line_total": _money(order.currency, line.line_total),
        }
        for line in order.lines.all()
    ]


def _render_notice(
    *,
    order: Order,
    store,
    sandbox: bool,
    headline: str,
    subject_prefix: str,
    intro: str,
    amount_label: str,
    amount: str,
    note: str = "",
    with_lines: bool = True,
    greeting: str | None = None,
    footer: str | None = None,
    action_label: str = "",
    action_url: str = "",
) -> RenderedEmail:
    """One layout for every notice. Defaults address the buyer; sellers override them."""
    context = {
        "store_name": store.name,
        "customer_name": order.customer.name,
        "order_number": order.number,
        "sandbox": sandbox,
        "headline": headline,
        "greeting": greeting if greeting is not None else f"Hi {order.customer.name},",
        "intro": intro,
        "amount_label": amount_label,
        "amount": amount,
        "note": note,
        "lines": _lines(order) if with_lines else [],
        "footer": footer
        if footer is not None
        else f"Questions? Reply to this email to reach {store.name}.",
        "action_label": action_label,
        "action_url": action_url,
    }
    subject = f"{subject_prefix} {order.number} - {amount}"
    if sandbox:
        subject = f"[Sandbox] {subject}"
    return RenderedEmail(
        subject=subject[:255],
        text=render_to_string("payments/email/order_notice.txt", context),
        html=render_to_string("payments/email/order_notice.html", context),
    )


def render_seller_payment_notice(
    *, order: Order, store, sandbox: bool, via: str, order_url: str
) -> RenderedEmail:
    """Tells the seller a payment landed, so they need not watch the order page."""
    return _render_notice(
        order=order,
        store=store,
        sandbox=sandbox,
        headline="You got paid",
        subject_prefix="You got paid:",
        intro=f"{order.customer.name} paid order {order.number} through {via}.",
        amount_label="Amount received",
        amount=_money(order.currency, order.total),
        greeting="Hi,",
        footer=f"Orbiz sent this because a PayPal payment arrived for {store.name}.",
        action_label="View order",
        action_url=order_url,
    )


def render_order_confirmation(*, order: Order, store, sandbox: bool) -> RenderedEmail:
    """Sent only when the seller opts in while confirming the order."""
    return _render_notice(
        order=order,
        store=store,
        sandbox=sandbox,
        headline="Order confirmed",
        subject_prefix="Order confirmed:",
        intro=f"{store.name} confirmed your order {order.number}. Here is what you ordered.",
        amount_label="Order total",
        amount=_money(order.currency, order.total),
        note=f"If payment is still due, {store.name} will send you a PayPal payment link separately.",
    )


def render_payment_receipt(*, order: Order, store, sandbox: bool) -> RenderedEmail:
    return _render_notice(
        order=order,
        store=store,
        sandbox=sandbox,
        headline="Payment received",
        subject_prefix="Payment received for",
        intro=f"{store.name} received your payment for order {order.number}. Thank you!",
        amount_label="Total paid",
        amount=_money(order.currency, order.total),
    )


def render_refund_notice(
    *, order: Order, store, sandbox: bool, amount, currency: str, fully: bool
) -> RenderedEmail:
    refunded = _money(currency, amount)
    return _render_notice(
        order=order,
        store=store,
        sandbox=sandbox,
        headline="Refund issued",
        subject_prefix="Refund issued for",
        intro=(
            f"{store.name} {'fully ' if fully else 'partially '}refunded order "
            f"{order.number}."
        ),
        amount_label="Refunded",
        amount=refunded,
        note=(
            "PayPal returns the money to your original payment method. It can take a "
            "few days to show up."
        ),
        with_lines=False,
    )


def _items_summary(order: Order, limit: int = 3, name_chars: int = 40) -> str:
    """A short one-liner of what was ordered (imported product titles can be very long)."""
    names = [Truncator(line.product_name).chars(name_chars) for line in order.lines.all()]
    if len(names) <= limit:
        return ", ".join(names)
    return f"{', '.join(names[:limit])} and {len(names) - limit} more"


def render_payment_request(
    *,
    order: Order,
    store,
    link: str,
    link_kind: str = CHECKOUT_LINK,
    kind: str = REQUEST,
    sandbox: bool,
    invoice_number: str = "",
    issued_on: date | None = None,
) -> RenderedEmail:
    """
    The email asking the buyer to pay.

    An invoice link reads like an invoice (number, issue date, due on receipt, priced lines,
    total due). A checkout link is a short "pay now" nudge: the link is meant for paying right
    away and can expire.
    """
    total = _money(order.currency, order.total)
    is_reminder = kind == REMINDER
    is_invoice = link_kind == INVOICE_LINK
    context = {
        "store_name": store.name,
        "customer_name": order.customer.name,
        "customer_email": order.customer.email,
        "order_number": order.number,
        "total": total,
        "lines": _lines(order),
        "items_summary": _items_summary(order),
        "link": link,
        "sandbox": sandbox,
        "is_reminder": is_reminder,
        "invoice_number": invoice_number or order.number,
        "issued_on": issued_on or timezone.localdate(),
    }
    if is_invoice:
        subject = f"Invoice {context['invoice_number']} from {store.name} - {total} due"
        template = "payments/email/invoice_request"
    else:
        subject = f"Pay {total} to {store.name} for order {order.number}"
        template = "payments/email/pay_now_request"
    if is_reminder:
        subject = f"Reminder: {subject}"
    if sandbox:
        subject = f"[Sandbox] {subject}"
    return RenderedEmail(
        subject=subject[:255],
        text=render_to_string(f"{template}.txt", context),
        html=render_to_string(f"{template}.html", context),
    )
