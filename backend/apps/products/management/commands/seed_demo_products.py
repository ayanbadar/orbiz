"""Seed demo catalog for hackathon judges: python manage.py seed_demo_products."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.products.models import Product
from apps.stores.models import StoreMembership
from apps.stores.services import create_store_for_user, get_default_store

User = get_user_model()

DEMO_PRODUCTS = [
    {
        "name": "Black Hoodie M",
        "sku": "HOOD-BLK-M",
        "description": "Classic midweight hoodie for demos.",
        "price": Decimal("49.00"),
        "stock_quantity": 12,
        "low_stock_threshold": 5,
        "channel3_product_id": "demo-c3-hoodie",
    },
    {
        "name": "White Tee S",
        "sku": "TEE-WHT-S",
        "description": "Everyday cotton tee.",
        "price": Decimal("19.00"),
        "stock_quantity": 40,
        "low_stock_threshold": 8,
        "channel3_product_id": "",
    },
    {
        "name": "Navy Cap",
        "sku": "CAP-NVY",
        "description": "Adjustable dad cap.",
        "price": Decimal("24.00"),
        "stock_quantity": 3,
        "low_stock_threshold": 5,
        "channel3_product_id": "",
    },
    {
        "name": "Canvas Tote",
        "sku": "TOTE-CNV",
        "description": "Reusable tote bag.",
        "price": Decimal("15.00"),
        "stock_quantity": 2,
        "low_stock_threshold": 5,
        "channel3_product_id": "",
    },
    {
        "name": "Running Socks 3-Pack",
        "sku": "SOCK-RUN-3",
        "description": "Breathable athletic socks.",
        "price": Decimal("18.00"),
        "stock_quantity": 25,
        "low_stock_threshold": 6,
        "channel3_product_id": "",
    },
    {
        "name": "Water Bottle 750ml",
        "sku": "BTL-750",
        "description": "Insulated steel bottle.",
        "price": Decimal("32.00"),
        "stock_quantity": 9,
        "low_stock_threshold": 4,
        "channel3_product_id": "demo-c3-bottle",
    },
    {
        "name": "Desk Mat XL",
        "sku": "MAT-DSK-XL",
        "description": "Non-slip desk mat.",
        "price": Decimal("28.00"),
        "stock_quantity": 1,
        "low_stock_threshold": 3,
        "channel3_product_id": "",
    },
    {
        "name": "Wireless Mouse",
        "sku": "MSE-WLS",
        "description": "Quiet click wireless mouse.",
        "price": Decimal("35.00"),
        "stock_quantity": 14,
        "low_stock_threshold": 5,
        "channel3_product_id": "",
    },
    {
        "name": "USB-C Hub",
        "sku": "HUB-USBC",
        "description": "7-in-1 USB-C hub.",
        "price": Decimal("55.00"),
        "stock_quantity": 6,
        "low_stock_threshold": 4,
        "channel3_product_id": "",
    },
    {
        "name": "Sticker Pack",
        "sku": "STK-PK",
        "description": "Assorted vinyl stickers.",
        "price": Decimal("8.00"),
        "stock_quantity": 0,
        "low_stock_threshold": 10,
        "channel3_product_id": "",
    },
]


class Command(BaseCommand):
    help = "Seed 10 demo products (mixed stock; 2 with Channel3 ids) for the default store."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            default="",
            help="Owner email whose default store receives the seed. Defaults to first store owner.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing demo SKUs for that store before seeding.",
        )

    def handle(self, *args, **options):
        email = (options.get("email") or "").strip().lower()
        user = self._resolve_user(email)
        store = get_default_store(user)
        if store is None:
            store = create_store_for_user(
                user=user,
                name="Demo Store",
                currency="USD",
                timezone="UTC",
                business_type="social",
            )
            self.stdout.write(self.style.WARNING(f"Created store '{store.name}' for {user.email}."))

        skus = [row["sku"] for row in DEMO_PRODUCTS]
        if options["replace"]:
            deleted, _ = Product.objects.filter(store=store, sku__in=skus).delete()
            self.stdout.write(f"Removed {deleted} existing demo product row(s).")

        created = 0
        skipped = 0
        for row in DEMO_PRODUCTS:
            if Product.objects.filter(store=store, sku=row["sku"]).exists():
                skipped += 1
                continue
            Product.objects.create(
                store=store,
                name=row["name"],
                sku=row["sku"],
                description=row["description"],
                price=row["price"],
                currency=store.currency,
                stock_quantity=row["stock_quantity"],
                low_stock_threshold=row["low_stock_threshold"],
                channel3_product_id=row["channel3_product_id"],
                channel3_source=(
                    {"title": row["name"], "demo": True} if row["channel3_product_id"] else None
                ),
                is_active=True,
            )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded store '{store.name}' (id={store.pk}): created={created}, skipped={skipped}. "
                "Try Channel3 search: black hoodie"
            )
        )

    def _resolve_user(self, email: str):
        if email:
            try:
                return User.objects.get(email__iexact=email)
            except User.DoesNotExist as exc:
                raise CommandError(f"No user with email {email!r}.") from exc

        membership = (
            StoreMembership.objects.select_related("user")
            .filter(role=StoreMembership.Role.OWNER)
            .order_by("created_at")
            .first()
        )
        if membership:
            return membership.user

        user = User.objects.order_by("id").first()
        if user is None:
            raise CommandError("No users exist. Create a seller account first.")
        return user
