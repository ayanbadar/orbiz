"""Fill stores with realistic products, customers and 90 days of orders.

    python manage.py seed_dashboard_data                      # every store
    python manage.py seed_dashboard_data --store Store1 --store Store2
    python manage.py seed_dashboard_data --reset              # remove seeded rows first

Unlike seed_demo_orders (a handful of orders, all dated today), this spreads orders
over the last 90 days with a growing trend and a mix of statuses, so the dashboard
charts have something to show. Everything it creates is tagged so --reset can remove
it without touching real data: orders carry "[seed]" in internal_notes, customers use
the @seed.example domain and products use the SD- SKU prefix.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.customers.models import Customer
from apps.orders.models import Order, OrderLine
from apps.orders.services import _next_order_number
from apps.products.models import Product
from apps.stores.models import Store

SEED_TAG = "[seed]"
SEED_EMAIL_DOMAIN = "@seed.example"
SEED_SKU_PREFIX = "SD-"

DAYS = 90
CUSTOMER_COUNT = 18

Fulfilment = Order.FulfilmentStatus
Payment = Order.PaymentStatus

# (name, sku, price, stock, low-stock threshold). Stock is mixed on purpose so the
# "Low stock" panel has both low and out-of-stock rows.
CATALOG = [
    ("Black Hoodie", "HOOD-BLK", "49.00", 42, 8),
    ("White Tee", "TEE-WHT", "19.00", 120, 20),
    ("Navy Cap", "CAP-NVY", "24.00", 4, 10),
    ("Canvas Tote", "TOTE-CNV", "15.00", 60, 10),
    ("Running Socks 3-Pack", "SOCK-RUN", "18.00", 85, 15),
    ("Water Bottle 750ml", "BTL-750", "32.00", 3, 8),
    ("Desk Mat XL", "MAT-DSK", "28.00", 0, 5),
    ("Wireless Mouse", "MSE-WLS", "35.00", 30, 6),
    ("USB-C Hub", "HUB-USBC", "55.00", 22, 5),
    ("Sticker Pack", "STK-PK", "8.00", 0, 15),
    ("Leather Wallet", "WLT-LTH", "42.00", 18, 5),
    ("Phone Stand", "STD-PHN", "12.00", 6, 10),
]

FIRST_NAMES = ["Ayesha", "Bilal", "Sara", "Hamza", "Zainab", "Omar", "Fatima", "Ali", "Hira", "Usman", "Maryam", "Danish"]
LAST_NAMES = ["Khan", "Ahmed", "Malik", "Sheikh", "Raza", "Hussain", "Qureshi", "Siddiqui", "Baig", "Farooq"]


def pick_status(rng: random.Random, age_days: float) -> tuple[str, str]:
    """Old orders are mostly finished; recent ones are spread across the pipeline."""
    roll = rng.random()
    if age_days > 14:
        if roll < 0.82:
            return Fulfilment.COMPLETED, Payment.PAID
        if roll < 0.90:
            return Fulfilment.CANCELLED, Payment.CANCELLED
        if roll < 0.96:
            return Fulfilment.COMPLETED, Payment.PARTIALLY_REFUNDED
        return Fulfilment.CANCELLED, Payment.REFUNDED
    for limit, status in [
        (0.35, (Fulfilment.COMPLETED, Payment.PAID)),
        (0.50, (Fulfilment.SHIPPED, Payment.PAID)),
        (0.62, (Fulfilment.PROCESSING, Payment.PAID)),
        (0.78, (Fulfilment.UNFULFILLED, Payment.UNPAID)),
        (0.84, (Fulfilment.UNFULFILLED, Payment.PENDING)),
        (0.88, (Fulfilment.UNFULFILLED, Payment.FAILED)),
        (0.93, (Fulfilment.CANCELLED, Payment.CANCELLED)),
    ]:
        if roll < limit:
            return status
    return Fulfilment.DRAFT, Payment.UNPAID


class Command(BaseCommand):
    help = "Seed products, customers and 90 days of orders so the dashboards have data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--store",
            action="append",
            default=[],
            help="Store name to seed (repeatable). Defaults to every store.",
        )
        parser.add_argument("--orders", type=int, default=140, help="Orders per store (default 140).")
        parser.add_argument("--reset", action="store_true", help="Remove previously seeded rows first.")

    def handle(self, *args, **options):
        stores = self._stores(options["store"])
        for store in stores:
            if options["reset"]:
                self._reset(store)
            self._seed(store, max(1, options["orders"]))

    def _stores(self, names: list[str]):
        stores = Store.objects.all().order_by("id")
        if names:
            wanted = {name.strip().lower() for name in names}
            stores = [s for s in stores if s.name.lower() in wanted]
            missing = wanted - {s.name.lower() for s in stores}
            if missing:
                raise CommandError(f"No store named: {', '.join(sorted(missing))}")
        stores = list(stores)
        if not stores:
            raise CommandError("There are no stores to seed. Create a store first.")
        return stores

    def _reset(self, store: Store) -> None:
        Order.objects.filter(store=store, internal_notes__startswith=SEED_TAG).delete()
        try:
            Customer.objects.filter(store=store, email__endswith=SEED_EMAIL_DOMAIN).delete()
            Product.objects.filter(store=store, sku__startswith=SEED_SKU_PREFIX).delete()
        except ProtectedError:
            self.stdout.write(
                self.style.WARNING(
                    f"{store.name}: kept seeded customers/products that real orders still use."
                )
            )
        self.stdout.write(f"{store.name}: removed earlier seed data.")

    @transaction.atomic
    def _seed(self, store: Store, order_count: int) -> None:
        # Lock the store row: order numbers are allocated under it.
        store = Store.objects.select_for_update().get(pk=store.pk)
        rng = random.Random(store.pk)  # same data every run for the same store
        now = timezone.now()

        products = self._products(store)
        customers = self._customers(store)
        weights = [len(products) - i for i in range(len(products))]  # earlier = more popular

        first_order_at: dict[int, object] = {}
        number = int(_next_order_number(store=store).split("-", 1)[1])
        created = 0

        for _ in range(order_count):
            # Squaring-style skew: more orders recently than long ago, so charts trend up.
            age_days = DAYS * rng.random() ** 1.5
            placed_at = now - timedelta(days=age_days, hours=rng.uniform(0, 12))
            if placed_at > now:
                placed_at = now
            fulfilment, payment = pick_status(rng, age_days)
            customer = rng.choice(customers)

            picked: dict[int, Product] = {}
            for _line in range(rng.choice([1, 1, 2, 2, 3])):
                product = rng.choices(products, weights)[0]
                picked[product.pk] = product
            lines = [(p, rng.randint(1, 3)) for p in picked.values()]
            total = sum((p.price * qty for p, qty in lines), Decimal("0.00"))

            order = Order.objects.create(
                store=store,
                number=f"ORD-{number}",
                customer=customer,
                currency=store.currency,
                subtotal=total,
                total=total,
                fulfilment_status=fulfilment,
                payment_status=payment,
                internal_notes=f"{SEED_TAG} dashboard data",
                confirmed_at=None if fulfilment == Fulfilment.DRAFT else placed_at,
                cancelled_at=placed_at if fulfilment == Fulfilment.CANCELLED else None,
            )
            number += 1
            OrderLine.objects.bulk_create(
                OrderLine(
                    order=order,
                    product=p,
                    product_name=p.name,
                    sku=p.sku,
                    unit_price=p.price,
                    quantity=qty,
                    line_total=p.price * qty,
                )
                for p, qty in lines
            )
            # created_at is auto_now_add, so backdate with an update.
            Order.objects.filter(pk=order.pk).update(created_at=placed_at, updated_at=placed_at)
            earliest = first_order_at.get(customer.pk)
            if earliest is None or placed_at < earliest:
                first_order_at[customer.pk] = placed_at
            created += 1

        # A customer cannot be created after their first order.
        for customer in customers:
            joined = first_order_at.get(customer.pk)
            joined = (joined - timedelta(hours=1)) if joined else now - timedelta(days=rng.randint(1, DAYS))
            Customer.objects.filter(pk=customer.pk).update(created_at=joined)

        self.stdout.write(
            self.style.SUCCESS(
                f"{store.name}: {len(products)} products, {len(customers)} customers, {created} orders."
            )
        )

    def _products(self, store: Store) -> list[Product]:
        products = []
        for name, sku, price, stock, threshold in CATALOG:
            product, _ = Product.objects.get_or_create(
                store=store,
                sku=f"{SEED_SKU_PREFIX}{sku}",
                defaults={
                    "name": name,
                    "price": Decimal(price),
                    "currency": store.currency,
                    "stock_quantity": stock,
                    "low_stock_threshold": threshold,
                },
            )
            products.append(product)
        return products

    def _customers(self, store: Store) -> list[Customer]:
        customers = []
        for i in range(CUSTOMER_COUNT):
            first = FIRST_NAMES[i % len(FIRST_NAMES)]
            last = LAST_NAMES[(i * 3) % len(LAST_NAMES)]
            customer, _ = Customer.objects.get_or_create(
                store=store,
                email=f"{first}.{last}.{i}{SEED_EMAIL_DOMAIN}".lower(),
                defaults={"name": f"{first} {last}", "phone": f"+92300{1000000 + i}"},
            )
            customers.append(customer)
        return customers
