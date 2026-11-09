from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.common.testing import create_active_store
from apps.customers.models import Customer
from apps.orders.models import Order, OrderLine
from apps.products.models import Product
from apps.stores.models import Role, StoreMembership

PASSWORD = "Orb1z-pass"
STORE_URL = "/api/v1/dashboard/summary/"
ADMIN_URL = "/api/v1/admin/dashboard/summary/"

TEST_SETTINGS = dict(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)

Fulfilment = Order.FulfilmentStatus
Payment = Order.PaymentStatus


def make_order(store, customer, *, total, fulfilment, payment, currency="USD", days_ago=0):
    order = Order.objects.create(
        store=store,
        number=f"ORD-{Order.objects.filter(store=store).count() + 1001}",
        customer=customer,
        currency=currency,
        subtotal=Decimal(total),
        total=Decimal(total),
        fulfilment_status=fulfilment,
        payment_status=payment,
    )
    # created_at is auto_now_add, so backdate with an update.
    when = timezone.now() - timedelta(days=days_ago)
    Order.objects.filter(pk=order.pk).update(created_at=when)
    order.refresh_from_db()
    return order


@override_settings(**TEST_SETTINGS)
class StoreDashboardTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="admin@example.com", password=PASSWORD)
        self.other_user = User.objects.create_user(email="other@example.com", password=PASSWORD)
        self.store = create_active_store(user=self.user, name="Mine", currency="USD")
        self.other_store = create_active_store(user=self.other_user, name="Theirs", currency="USD")
        self.customer = Customer.objects.create(store=self.store, name="Ayesha")
        self.other_customer = Customer.objects.create(store=self.other_store, name="Zed")
        self.product = Product.objects.create(
            store=self.store, name="Hoodie", sku="H-1", price=Decimal("50"),
            currency="USD", stock_quantity=2, low_stock_threshold=5,
        )

    def get(self, user=None, **params):
        self.client.force_authenticate(user or self.user)
        return self.client.get(STORE_URL, params)

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(STORE_URL).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_without_orders_read_is_forbidden(self):
        staff = User.objects.create_user(email="staff@example.com", password=PASSWORD)
        role = Role.objects.create(store=self.store, name="Stock", permissions=["products.read"])
        StoreMembership.objects.create(store=self.store, user=staff, role=role)
        self.assertEqual(self.get(staff).status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_with_orders_read_can_view(self):
        staff = User.objects.create_user(email="staff@example.com", password=PASSWORD)
        role = Role.objects.create(store=self.store, name="Sales", permissions=["orders.read"])
        StoreMembership.objects.create(store=self.store, user=staff, role=role)
        self.assertEqual(self.get(staff).status_code, status.HTTP_200_OK)

    def test_revenue_counts_only_paid_sales(self):
        make_order(self.store, self.customer, total="100", fulfilment=Fulfilment.COMPLETED, payment=Payment.PAID)
        make_order(self.store, self.customer, total="40", fulfilment=Fulfilment.UNFULFILLED, payment=Payment.PARTIALLY_REFUNDED)
        make_order(self.store, self.customer, total="30", fulfilment=Fulfilment.UNFULFILLED, payment=Payment.UNPAID)
        make_order(self.store, self.customer, total="500", fulfilment=Fulfilment.DRAFT, payment=Payment.PAID)
        make_order(self.store, self.customer, total="500", fulfilment=Fulfilment.CANCELLED, payment=Payment.PAID)
        make_order(self.store, self.customer, total="500", fulfilment=Fulfilment.COMPLETED, payment=Payment.REFUNDED)

        kpis = self.get().data["kpis"]
        self.assertEqual(kpis["revenue"]["value"], "140.00")
        self.assertEqual(kpis["orders"]["value"], 4)  # drafts and cancelled are not sales
        self.assertEqual(kpis["average_order_value"]["value"], "70.00")
        self.assertEqual(self.get().data["open_orders"], 3)

    def test_previous_period_and_range_filter(self):
        make_order(self.store, self.customer, total="100", fulfilment=Fulfilment.COMPLETED, payment=Payment.PAID, days_ago=2)
        make_order(self.store, self.customer, total="60", fulfilment=Fulfilment.COMPLETED, payment=Payment.PAID, days_ago=10)

        week = self.get(range="7d").data["kpis"]["revenue"]
        self.assertEqual((week["value"], week["previous"]), ("100.00", "60.00"))
        month = self.get(range="30d").data["kpis"]["revenue"]
        self.assertEqual(month["value"], "160.00")

    def test_unknown_range_falls_back_to_default(self):
        self.assertEqual(self.get(range="bogus").data["range"], "30d")

    def test_series_is_zero_filled(self):
        make_order(self.store, self.customer, total="25", fulfilment=Fulfilment.COMPLETED, payment=Payment.PAID)
        series = self.get(range="7d").data["series"]
        self.assertEqual(len(series), 7)
        self.assertEqual(sum(p["orders"] for p in series), 1)
        self.assertEqual(series[0]["orders"], 0)

    def test_top_products_low_stock_and_recent_orders(self):
        order = make_order(self.store, self.customer, total="100", fulfilment=Fulfilment.COMPLETED, payment=Payment.PAID)
        OrderLine.objects.create(
            order=order, product=self.product, product_name="Hoodie", sku="H-1",
            unit_price=Decimal("50"), quantity=2, line_total=Decimal("100"),
        )
        data = self.get().data
        self.assertEqual(data["top_products"][0]["quantity"], 2)
        self.assertEqual(data["low_stock"][0]["sku"], "H-1")
        self.assertEqual(data["recent_orders"][0]["number"], order.number)

    def test_other_stores_data_never_leaks(self):
        order = make_order(self.other_store, self.other_customer, total="999", fulfilment=Fulfilment.COMPLETED, payment=Payment.PAID)
        theirs = Product.objects.create(
            store=self.other_store, name="Secret", sku="S-1", price=Decimal("1"),
            currency="USD", stock_quantity=0,
        )
        OrderLine.objects.create(
            order=order, product=theirs, product_name="Secret", sku="S-1",
            unit_price=Decimal("999"), quantity=1, line_total=Decimal("999"),
        )
        data = self.get().data
        self.assertEqual(data["kpis"]["revenue"]["value"], "0.00")
        self.assertEqual(data["kpis"]["new_customers"]["value"], 1)
        self.assertEqual(data["top_products"], [])
        self.assertEqual(data["recent_orders"], [])
        self.assertEqual([p["sku"] for p in data["low_stock"]], ["H-1"])

    def test_superuser_without_store_is_not_served(self):
        root = User.objects.create_superuser(email="root@example.com", password=PASSWORD)
        self.assertNotEqual(self.get(root).status_code, status.HTTP_200_OK)


@override_settings(**TEST_SETTINGS)
class PlatformDashboardTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.root = User.objects.create_superuser(email="root@example.com", password=PASSWORD)
        self.seller = User.objects.create_user(email="seller@example.com", password=PASSWORD)
        self.store_usd = create_active_store(user=self.seller, name="USD Shop", currency="USD")
        eu = User.objects.create_user(email="eu@example.com", password=PASSWORD)
        self.store_eur = create_active_store(user=eu, name="EUR Shop", currency="EUR")

    def get(self, user):
        self.client.force_authenticate(user)
        return self.client.get(ADMIN_URL)

    def test_requires_superuser(self):
        self.assertEqual(self.client.get(ADMIN_URL).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.get(self.seller).status_code, status.HTTP_403_FORBIDDEN)

    def test_totals_and_status_counts(self):
        data = self.get(self.root).data
        self.assertEqual(data["totals"]["stores"], 2)
        self.assertEqual(data["totals"]["users"], 2)  # the superuser is not counted
        self.assertEqual({r["status"]: r["count"] for r in data["stores_by_status"]}, {"active": 2})
        self.assertEqual(len(data["series"]), 30)

    def test_order_totals_are_grouped_by_currency(self):
        usd = Customer.objects.create(store=self.store_usd, name="A")
        eur = Customer.objects.create(store=self.store_eur, name="B")
        make_order(self.store_usd, usd, total="100", fulfilment=Fulfilment.COMPLETED, payment=Payment.PAID)
        make_order(self.store_usd, usd, total="50", fulfilment=Fulfilment.COMPLETED, payment=Payment.PAID)
        make_order(self.store_eur, eur, total="70", fulfilment=Fulfilment.COMPLETED, payment=Payment.PAID, currency="EUR")
        make_order(self.store_eur, eur, total="70", fulfilment=Fulfilment.DRAFT, payment=Payment.UNPAID, currency="EUR")

        data = self.get(self.root).data
        by_currency = {r["currency"]: r for r in data["orders_by_currency"]}
        self.assertEqual(by_currency["USD"]["revenue"], "150.00")
        self.assertEqual(by_currency["USD"]["orders"], 2)
        self.assertEqual(by_currency["EUR"]["revenue"], "70.00")
        self.assertEqual(by_currency["EUR"]["orders"], 1)
        self.assertEqual(data["top_stores"][0]["name"], "USD Shop")


@override_settings(**TEST_SETTINGS)
class SeedCommandTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="seed@example.com", password=PASSWORD)
        self.store = create_active_store(user=self.user, name="Store1")

    def seed(self, *args):
        call_command("seed_dashboard_data", *args, stdout=StringIO())

    def test_seeded_data_shows_up_on_the_dashboard(self):
        self.seed("--store", "Store1", "--orders", "60")
        self.assertEqual(Order.objects.filter(store=self.store).count(), 60)

        self.client.force_authenticate(self.user)
        data = self.client.get(STORE_URL, {"range": "90d"}).data
        self.assertGreater(Decimal(data["kpis"]["revenue"]["value"]), 0)
        self.assertGreater(len(data["top_products"]), 0)
        self.assertGreater(len(data["low_stock"]), 0)

    def test_reset_makes_reruns_idempotent(self):
        self.seed("--orders", "20")
        self.seed("--orders", "20", "--reset")
        self.assertEqual(Order.objects.filter(store=self.store).count(), 20)
        self.assertEqual(Product.objects.filter(store=self.store).count(), 12)

    def test_unknown_store_is_an_error(self):
        with self.assertRaises(CommandError):
            self.seed("--store", "Nope")
