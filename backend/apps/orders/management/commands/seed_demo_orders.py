"""Seed demo customers + orders: python manage.py seed_demo_orders --email=..."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.customers.models import Customer
from apps.customers.services import create_customer
from apps.orders.models import Order
from apps.orders.services import (
    cancel_order,
    confirm_order,
    create_draft,
    mark_order_paid,
    transition_fulfilment,
)
from apps.products.models import Product
from apps.stores.services import get_default_store

User = get_user_model()

# Max concurrent deductions before restores: products[0] needs 3, [1] needs 2, [2] needs 1.
MIN_STOCK = (3, 2, 1)


class Command(BaseCommand):
    help = "Seed demo customers and orders (mixed statuses) for the seller's default store."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            required=True,
            help="Seller account email (must already have a store and products).",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo-tagged customers/orders for this store first.",
        )
        parser.add_argument(
            "--extra",
            type=int,
            default=25,
            help="Extra draft orders so the list paginates (default page size is 20).",
        )

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise CommandError(f"No user with email {email}") from exc

        store = get_default_store(user)
        if store is None:
            raise CommandError("User has no store. Create a workspace first.")

        products = self._pick_products(store)
        if len(products) < 2:
            raise CommandError(
                "Need at least 2 active products with stock. "
                "Run: python manage.py seed_demo_products --email=... --replace"
            )

        if options["reset"]:
            demo_customers = Customer.objects.filter(
                store=store, notes__startswith="[demo]"
            )
            # Orders first (customer FK is PROTECT).
            Order.objects.filter(
                store=store, internal_notes__startswith="[demo]"
            ).delete()
            Order.objects.filter(store=store, customer__in=demo_customers).delete()
            deleted_customers, _ = demo_customers.delete()
            self.stdout.write(
                f"Cleared previous demo orders/customers ({deleted_customers} customers)."
            )

        c1 = self._demo_customer(
            store=store,
            name="Ayesha Khan",
            email="ayesha.demo@example.com",
            phone="+92 300 0000001",
            notes="[demo] Clifton buyer",
        )
        c2 = self._demo_customer(
            store=store,
            name="Bilal Ahmed",
            email="bilal.demo@example.com",
            phone="+92 300 0000002",
            notes="[demo] Repeat customer",
        )
        c3 = self._demo_customer(
            store=store,
            name="Sana Malik",
            email="sana.demo@example.com",
            phone="+92 300 0000003",
            notes="[demo] Pagination customer",
        )

        draft = create_draft(
            store=store,
            user=user,
            customer=c1,
            lines=[{"product_id": products[0].id, "quantity": 1}],
            delivery_notes="Deliver to Clifton",
            internal_notes="[demo] draft",
            source_message="Hi, I need one black hoodie in medium.",
        )

        awaiting = create_draft(
            store=store,
            user=user,
            customer=c1,
            lines=[{"product_id": products[0].id, "quantity": 2}],
            delivery_notes="Clifton",
            internal_notes="[demo] unfulfilled pending payment",
            source_message="Two hoodies please.",
        )
        confirm_order(order=awaiting, user=user)

        processing = create_draft(
            store=store,
            user=user,
            customer=c2,
            lines=[{"product_id": products[1].id, "quantity": 1}],
            delivery_notes="DHA Phase 5",
            internal_notes="[demo] processing",
        )
        confirm_order(order=processing, user=user)
        mark_order_paid(order=processing, user=user, message="[demo] simulated paid")
        transition_fulfilment(
            order=processing,
            user=user,
            fulfilment_status=Order.FulfilmentStatus.PROCESSING,
        )

        shipped = create_draft(
            store=store,
            user=user,
            customer=c2,
            lines=[
                {"product_id": products[1].id, "quantity": 1},
                {"product_id": products[min(2, len(products) - 1)].id, "quantity": 1},
            ],
            delivery_notes="Gulshan",
            internal_notes="[demo] shipped",
        )
        confirm_order(order=shipped, user=user)
        mark_order_paid(order=shipped, user=user, message="[demo] simulated paid")
        transition_fulfilment(
            order=shipped, user=user, fulfilment_status=Order.FulfilmentStatus.PROCESSING
        )
        transition_fulfilment(
            order=shipped, user=user, fulfilment_status=Order.FulfilmentStatus.SHIPPED
        )

        cancelled = create_draft(
            store=store,
            user=user,
            customer=c1,
            lines=[{"product_id": products[0].id, "quantity": 1}],
            internal_notes="[demo] cancelled",
        )
        confirm_order(order=cancelled, user=user)
        cancel_order(order=cancelled, user=user)

        customers = (c1, c2, c3)
        extra = max(0, int(options["extra"]))
        for i in range(extra):
            customer = customers[i % len(customers)]
            product = products[i % len(products)]
            create_draft(
                store=store,
                user=user,
                customer=customer,
                lines=[{"product_id": product.id, "quantity": 1}],
                delivery_notes="Demo pagination row",
                internal_notes=f"[demo] list-page {i + 1:02d}",
                source_message=f"Pagination filler order #{i + 1}",
            )

        total = Order.objects.filter(
            store=store, internal_notes__startswith="[demo]"
        ).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded customers {c1.id},{c2.id},{c3.id}; showcase + {extra} list rows "
                f"({total} demo orders total; products {[p.sku for p in products]}). "
                f"Draft showcase: {draft.number}."
            )
        )

    def _demo_customer(self, *, store, name, email, phone, notes) -> Customer:
        existing = Customer.objects.filter(store=store, email=email).first()
        if existing:
            return existing
        return create_customer(
            store=store,
            name=name,
            email=email,
            phone=phone,
            notes=notes,
        )

    def _pick_products(self, store) -> list[Product]:
        """
        Pick by on-hand stock only — never by SKU or other catalog identifiers.

        Ordering by id alone fails when older depleted rows (stock 0) sort
        before newer well-stocked rows. Stock is the operational constraint
        confirm_order already enforces.
        """
        qs = Product.objects.filter(store=store, is_active=True).order_by(
            "-stock_quantity", "-id"
        )
        picked: list[Product] = []
        for product in qs:
            need = MIN_STOCK[len(picked)] if len(picked) < len(MIN_STOCK) else 1
            if product.stock_quantity < need:
                continue
            picked.append(product)
            if len(picked) >= 3:
                break
        return picked


