from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.products.models import Product
from apps.stores.services import create_store_for_user

PASSWORD = "Orb1z-pass"

TEST_SETTINGS = dict(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)


@override_settings(**TEST_SETTINGS)
class SeedDemoProductsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="seed@example.com",
            password=PASSWORD,
            first_name="Seed",
        )
        self.store = create_store_for_user(
            user=self.user,
            name="Seed Store",
            currency="USD",
            timezone="UTC",
            business_type="social",
        )

    def test_seed_creates_demo_catalog(self):
        out = StringIO()
        call_command("seed_demo_products", email=self.user.email, stdout=out)
        products = Product.objects.filter(store=self.store)
        self.assertGreaterEqual(products.count(), 8)
        self.assertTrue(products.filter(channel3_product_id__gt="").exists())
        self.assertTrue(products.filter(stock_quantity=0).exists())
        self.assertIn("created=", out.getvalue())

    def test_seed_is_idempotent_without_replace(self):
        call_command("seed_demo_products", email=self.user.email, stdout=StringIO())
        first = Product.objects.filter(store=self.store).count()
        call_command("seed_demo_products", email=self.user.email, stdout=StringIO())
        self.assertEqual(Product.objects.filter(store=self.store).count(), first)
