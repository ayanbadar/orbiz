"""Dashboard numbers, computed with ORM aggregates.

Definitions (kept in one place so every chart agrees):
- A "sale" is an order that is neither draft nor cancelled.
- "Revenue" is the total of sales whose payment is PAID_LIKE (paid / partially refunded).
- "Open orders" reuses the Orders page's own definition.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Count, F, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.billing.models import Payment, Subscription
from apps.customers.models import Customer
from apps.customers.views import OPEN_FULFILMENT_STATUSES
from apps.orders.models import Order, OrderLine
from apps.orders.services import PAID_LIKE
from apps.products.models import Product
from apps.stores.models import Store

RANGES = {"7d": 7, "30d": 30, "90d": 90}
DEFAULT_RANGE = "30d"
CACHE_SECONDS = 60
TOP_LIMIT = 5

ZERO = Decimal("0.00")
PAID = Q(payment_status__in=PAID_LIKE)


def parse_range(raw: str | None) -> str:
    """Return a valid range key; anything unknown falls back to the default."""
    return raw if raw in RANGES else DEFAULT_RANGE


class Window:
    """The selected period and the equally long one before it, in a given time zone."""

    def __init__(self, range_key: str, tz: ZoneInfo):
        self.days = RANGES[range_key]
        self.tz = tz
        self.today: date = timezone.now().astimezone(tz).date()
        self.first_day: date = self.today - timedelta(days=self.days - 1)
        self.start = self._midnight(self.first_day)
        self.previous_start = self._midnight(self.first_day - timedelta(days=self.days))

    def _midnight(self, day: date) -> datetime:
        return datetime.combine(day, time.min, tzinfo=self.tz)

    def dates(self) -> list[date]:
        return [self.first_day + timedelta(days=i) for i in range(self.days)]


def _store_tz(store: Store) -> ZoneInfo:
    try:
        return ZoneInfo(store.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _sales(qs):
    return qs.exclude(
        fulfilment_status__in=[Order.FulfilmentStatus.DRAFT, Order.FulfilmentStatus.CANCELLED]
    )


def _counts(qs, field: str) -> list[dict]:
    rows = qs.values(field).annotate(count=Count("id")).order_by("-count")
    return [{"status": row[field], "count": row["count"]} for row in rows]


def _kpi(current, previous) -> dict:
    return {"value": current or 0, "previous": previous or 0}


def _money_kpi(current, previous) -> dict:
    return {"value": current or ZERO, "previous": previous or ZERO}


def _cached(key: str, build):
    data = cache.get(key)
    if data is None:
        data = build()
        cache.set(key, data, CACHE_SECONDS)
    return data


# ---------------------------------------------------------------- store dashboard


def store_summary(store: Store, range_key: str) -> dict:
    return _cached(
        f"dashboard:store:{store.id}:{range_key}",
        lambda: _build_store_summary(store, range_key),
    )


def _build_store_summary(store: Store, range_key: str) -> dict:
    window = Window(range_key, _store_tz(store))
    orders = Order.objects.filter(store=store)
    sales = _sales(orders)
    in_period = Q(created_at__gte=window.start)
    in_previous = Q(created_at__gte=window.previous_start, created_at__lt=window.start)

    totals = sales.filter(created_at__gte=window.previous_start).aggregate(
        revenue=Sum("total", filter=PAID & in_period),
        previous_revenue=Sum("total", filter=PAID & in_previous),
        orders=Count("id", filter=in_period),
        previous_orders=Count("id", filter=in_previous),
        paid_orders=Count("id", filter=PAID & in_period),
        previous_paid_orders=Count("id", filter=PAID & in_previous),
    )
    customers = Customer.objects.filter(store=store).aggregate(
        current=Count("id", filter=in_period),
        previous=Count("id", filter=in_previous),
    )

    def average(revenue, paid_orders):
        return (revenue / paid_orders).quantize(ZERO) if revenue and paid_orders else ZERO

    kpis = {
        "revenue": _money_kpi(totals["revenue"], totals["previous_revenue"]),
        "orders": _kpi(totals["orders"], totals["previous_orders"]),
        "average_order_value": _money_kpi(
            average(totals["revenue"], totals["paid_orders"]),
            average(totals["previous_revenue"], totals["previous_paid_orders"]),
        ),
        "new_customers": _kpi(customers["current"], customers["previous"]),
    }

    period_orders = orders.filter(in_period)
    return {
        "range": range_key,
        "currency": store.currency,
        "kpis": kpis,
        "open_orders": orders.filter(fulfilment_status__in=OPEN_FULFILMENT_STATUSES).count(),
        "orders_by_fulfilment": _counts(period_orders, "fulfilment_status"),
        "orders_by_payment": _counts(period_orders, "payment_status"),
        "series": _store_series(sales.filter(in_period), window),
        "top_products": _top_products(store, window),
        "low_stock": _low_stock(store),
        "recent_orders": _recent_orders(orders),
    }


def _store_series(period_sales, window: Window) -> list[dict]:
    rows = (
        period_sales.annotate(day=TruncDate("created_at", tzinfo=window.tz))
        .values("day")
        .annotate(orders=Count("id"), revenue=Sum("total", filter=PAID))
    )
    by_day = {row["day"]: row for row in rows}
    return [
        {
            "date": day,
            "orders": by_day[day]["orders"] if day in by_day else 0,
            "revenue": (by_day[day]["revenue"] or ZERO) if day in by_day else ZERO,
        }
        for day in window.dates()
    ]


def _top_products(store: Store, window: Window) -> list[dict]:
    rows = (
        OrderLine.objects.filter(
            order__store=store,
            order__created_at__gte=window.start,
            order__payment_status__in=PAID_LIKE,
        )
        .exclude(order__fulfilment_status=Order.FulfilmentStatus.CANCELLED)
        .values("product_id")
        .annotate(
            name=Max("product_name"),
            sku=Max("sku"),
            quantity=Sum("quantity"),
            revenue=Sum("line_total"),
        )
        .order_by("-revenue")[:TOP_LIMIT]
    )
    return list(rows)


def _low_stock(store: Store) -> list[dict]:
    return list(
        Product.objects.filter(
            store=store, is_active=True, stock_quantity__lte=F("low_stock_threshold")
        )
        .order_by("stock_quantity", "name")
        .values("id", "name", "sku", "stock_quantity", "low_stock_threshold")[:TOP_LIMIT]
    )


def _recent_orders(orders) -> list[dict]:
    rows = (
        orders.exclude(fulfilment_status=Order.FulfilmentStatus.DRAFT)
        .select_related("customer")
        .order_by("-created_at")[:TOP_LIMIT]
    )
    return [
        {
            "id": order.id,
            "number": order.number,
            "customer_name": order.customer.name,
            "total": order.total,
            "currency": order.currency,
            "fulfilment_status": order.fulfilment_status,
            "payment_status": order.payment_status,
            "created_at": order.created_at,
        }
        for order in rows
    ]


# ---------------------------------------------------------------- platform dashboard


def platform_summary(range_key: str) -> dict:
    return _cached(f"dashboard:platform:{range_key}", lambda: _build_platform_summary(range_key))


def _build_platform_summary(range_key: str) -> dict:
    window = Window(range_key, ZoneInfo("UTC"))
    User = get_user_model()
    in_period = Q(created_at__gte=window.start)
    in_previous = Q(created_at__gte=window.previous_start, created_at__lt=window.start)

    stores = Store.objects.aggregate(
        total=Count("id"),
        current=Count("id", filter=in_period),
        previous=Count("id", filter=in_previous),
    )
    users = User.objects.filter(is_superuser=False).aggregate(
        total=Count("id"), active=Count("id", filter=Q(is_active=True))
    )
    succeeded = Payment.objects.filter(status=Payment.Status.SUCCEEDED)
    subscription_revenue = succeeded.filter(created_at__gte=window.previous_start).aggregate(
        current=Sum("amount_cents", filter=in_period),
        previous=Sum("amount_cents", filter=in_previous),
    )

    sales = _sales(Order.objects.filter(created_at__gte=window.start))
    return {
        "range": range_key,
        "kpis": {
            "stores": _kpi(stores["current"], stores["previous"]),
            "subscription_revenue_cents": _kpi(
                subscription_revenue["current"], subscription_revenue["previous"]
            ),
        },
        "totals": {
            "stores": stores["total"],
            "users": users["total"],
            "active_users": users["active"],
        },
        "stores_by_status": _counts(Store.objects.all(), "status"),
        "subscriptions_by_status": _counts(Subscription.objects.all(), "status"),
        "series": _platform_series(succeeded, window),
        "orders_by_currency": _orders_by_currency(sales),
        "top_stores": _top_stores(sales),
    }


def _platform_series(succeeded_payments, window: Window) -> list[dict]:
    def per_day(qs, **aggregates):
        rows = qs.filter(created_at__gte=window.start).annotate(
            day=TruncDate("created_at", tzinfo=window.tz)
        )
        return {row["day"]: row for row in rows.values("day").annotate(**aggregates)}

    new_stores = per_day(Store.objects.all(), n=Count("id"))
    revenue = per_day(succeeded_payments, cents=Sum("amount_cents"))
    return [
        {
            "date": day,
            "new_stores": new_stores[day]["n"] if day in new_stores else 0,
            "subscription_revenue_cents": revenue[day]["cents"] if day in revenue else 0,
        }
        for day in window.dates()
    ]


def _orders_by_currency(sales) -> list[dict]:
    """Money is never added across currencies, so each currency gets its own row."""
    return list(
        sales.values("currency")
        .annotate(
            orders=Count("id"),
            stores=Count("store_id", distinct=True),
            revenue=Sum("total", filter=PAID),
        )
        .order_by("-orders")
    )


def _top_stores(sales) -> list[dict]:
    rows = (
        sales.values("store_id", "store__name", "currency")
        .annotate(orders=Count("id"), revenue=Sum("total", filter=PAID))
        .order_by("-orders")[:TOP_LIMIT]
    )
    return [
        {
            "store_id": row["store_id"],
            "name": row["store__name"],
            "currency": row["currency"],
            "orders": row["orders"],
            "revenue": row["revenue"] or ZERO,
        }
        for row in rows
    ]
