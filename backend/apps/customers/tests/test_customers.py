from datetime import timedelta

from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.stores.services import create_store_for_user

PASSWORD = "Orb1z-pass"

TEST_SETTINGS = dict(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)


@override_settings(**TEST_SETTINGS)
class CustomerApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="seller@example.com", password=PASSWORD, first_name="S"
        )
        self.other = User.objects.create_user(
            email="other@example.com", password=PASSWORD, first_name="O"
        )
        self.store = create_store_for_user(
            user=self.user,
            name="Demo Store",
            currency="USD",
            timezone="UTC",
            business_type="social",
        )
        create_store_for_user(
            user=self.other,
            name="Other Store",
            currency="USD",
            timezone="UTC",
            business_type="social",
        )

    def test_unauthenticated_rejected(self):
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_store_returns_404(self):
        lonely = User.objects.create_user(
            email="lonely@example.com", password=PASSWORD, first_name="L"
        )
        self.client.force_authenticate(lonely)
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_list_and_scope(self):
        self.client.force_authenticate(self.user)
        created = self.client.post(
            "/api/v1/customers/",
            {"name": "Ayesha Khan", "email": "ayesha@example.com", "phone": "+92"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["name"], "Ayesha Khan")

        listed = self.client.get("/api/v1/customers/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertIn("results", listed.data)
        self.assertEqual(len(listed.data["results"]), 1)

        self.client.force_authenticate(self.other)
        other_list = self.client.get("/api/v1/customers/")
        self.assertIn("results", other_list.data)
        self.assertEqual(len(other_list.data["results"]), 0)

        foreign = self.client.get(f"/api/v1/customers/{created.data['id']}/")
        self.assertEqual(foreign.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_name_rejected(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/customers/",
            {"name": "   "},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_patch_customer(self):
        self.client.force_authenticate(self.user)
        customer = Customer.objects.create(store=self.store, name="Old Name")
        patched = self.client.patch(
            f"/api/v1/customers/{customer.id}/",
            {"name": "New Name", "notes": "VIP"},
            format="json",
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertEqual(patched.data["name"], "New Name")
        self.assertEqual(patched.data["notes"], "VIP")

    def test_invalid_email_rejected(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/customers/",
            {"name": "Bad Email", "email": "not-an-email"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_patch_blank_name_rejected(self):
        self.client.force_authenticate(self.user)
        customer = Customer.objects.create(store=self.store, name="Keep Me")
        response = self.client.patch(
            f"/api/v1/customers/{customer.id}/", {"name": "  "}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        customer.refresh_from_db()
        self.assertEqual(customer.name, "Keep Me")


@override_settings(**TEST_SETTINGS)
class CustomerStatsApiTests(APITestCase):
    """List/detail order stats, sorting, and column filters for the customers grid."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="seller@example.com", password=PASSWORD, first_name="S"
        )
        self.store = create_store_for_user(
            user=self.user,
            name="Demo Store",
            currency="USD",
            timezone="UTC",
            business_type="social",
        )
        self.client.force_authenticate(self.user)
        now = timezone.now()
        self.repeat = Customer.objects.create(
            store=self.store, name="Ayesha Khan", email="ayesha@example.com", phone="+92 300"
        )
        self.once = Customer.objects.create(
            store=self.store, name="Bilal Ahmed", email="bilal@example.com", phone="+92 321"
        )
        self.never = Customer.objects.create(store=self.store, name="Che Lee")
        self._order(self.repeat, "ORD-1", now - timedelta(days=10))
        self._order(self.repeat, "ORD-2", now - timedelta(days=5))
        self._order(self.once, "ORD-3", now - timedelta(days=1))

    def _order(self, customer, number, created_at):
        order = Order.objects.create(
            store=self.store, number=number, customer=customer, currency="USD"
        )
        # created_at is auto_now_add; backdate so last-order sorting is deterministic.
        Order.objects.filter(pk=order.pk).update(created_at=created_at)
        return order

    def _names(self, query=""):
        response = self.client.get(f"/api/v1/customers/{query}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [row["name"] for row in response.data["results"]]

    def test_list_includes_order_stats(self):
        response = self.client.get("/api/v1/customers/")
        rows = {row["name"]: row for row in response.data["results"]}
        self.assertEqual(rows["Ayesha Khan"]["order_count"], 2)
        self.assertEqual(rows["Bilal Ahmed"]["order_count"], 1)
        self.assertEqual(rows["Che Lee"]["order_count"], 0)
        # All seeded orders default to draft, which counts as open.
        self.assertEqual(rows["Ayesha Khan"]["open_order_count"], 2)
        self.assertEqual(rows["Bilal Ahmed"]["open_order_count"], 1)
        self.assertEqual(rows["Che Lee"]["open_order_count"], 0)
        self.assertIsNone(rows["Che Lee"]["last_order_at"])
        latest = Order.objects.get(number="ORD-2").created_at
        self.assertEqual(parse_datetime(rows["Ayesha Khan"]["last_order_at"]), latest)

    def test_order_by_last_order_keeps_never_ordered_last(self):
        self.assertEqual(
            self._names("?ordering=-last_order_at"), ["Bilal Ahmed", "Ayesha Khan", "Che Lee"]
        )
        self.assertEqual(
            self._names("?ordering=last_order_at"), ["Ayesha Khan", "Bilal Ahmed", "Che Lee"]
        )

    def test_order_by_order_count(self):
        self.assertEqual(
            self._names("?ordering=-order_count"), ["Ayesha Khan", "Bilal Ahmed", "Che Lee"]
        )

    def test_column_filters(self):
        self.assertEqual(self._names("?name=bil"), ["Bilal Ahmed"])
        self.assertEqual(self._names("?email=ayesha"), ["Ayesha Khan"])
        self.assertEqual(self._names("?phone=321"), ["Bilal Ahmed"])
        self.assertEqual(self._names("?q=example.com"), ["Ayesha Khan", "Bilal Ahmed"])
        self.assertEqual(self._names("?orders_min=2"), ["Ayesha Khan"])
        self.assertEqual(self._names("?orders_max=0"), ["Che Lee"])
        self.assertEqual(self._names("?orders_min=1&orders_max=1"), ["Bilal Ahmed"])

    def test_bad_params_are_ignored(self):
        self.assertEqual(
            self._names("?orders_min=abc&orders_max=&ordering=drop_table"),
            ["Ayesha Khan", "Bilal Ahmed", "Che Lee"],
        )

    def test_detail_create_and_patch_include_stats(self):
        detail = self.client.get(f"/api/v1/customers/{self.repeat.id}/")
        self.assertEqual(detail.data["order_count"], 2)
        self.assertEqual(detail.data["open_order_count"], 2)

        patched = self.client.patch(
            f"/api/v1/customers/{self.repeat.id}/", {"notes": "VIP"}, format="json"
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertEqual(patched.data["order_count"], 2)
        self.assertEqual(patched.data["open_order_count"], 2)
        self.assertEqual(patched.data["notes"], "VIP")

        created = self.client.post("/api/v1/customers/", {"name": "New"}, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["order_count"], 0)
        self.assertEqual(created.data["open_order_count"], 0)
        self.assertIsNone(created.data["last_order_at"])

    def test_open_order_count_excludes_completed_and_cancelled(self):
        customer = Customer.objects.create(store=self.store, name="Mixed Statuses")

        def make(number, fulfilment_status):
            return Order.objects.create(
                store=self.store,
                number=number,
                customer=customer,
                currency="USD",
                fulfilment_status=fulfilment_status,
            )

        make("MIX-1", Order.FulfilmentStatus.DRAFT)
        make("MIX-2", Order.FulfilmentStatus.UNFULFILLED)
        make("MIX-3", Order.FulfilmentStatus.PROCESSING)
        make("MIX-4", Order.FulfilmentStatus.SHIPPED)
        make("MIX-5", Order.FulfilmentStatus.COMPLETED)
        make("MIX-6", Order.FulfilmentStatus.CANCELLED)

        response = self.client.get(f"/api/v1/customers/{customer.id}/")
        self.assertEqual(response.data["order_count"], 6)
        self.assertEqual(response.data["open_order_count"], 4)

    def test_needs_attention_filter(self):
        # repeat/once both have draft (open) orders from setUp; never has none.
        self.assertEqual(self._names("?needs_attention=true"), ["Ayesha Khan", "Bilal Ahmed"])

        Order.objects.filter(customer=self.repeat).update(
            fulfilment_status=Order.FulfilmentStatus.COMPLETED
        )
        self.assertEqual(self._names("?needs_attention=true"), ["Bilal Ahmed"])

    def test_order_by_open_order_count(self):
        self.assertEqual(
            self._names("?ordering=-open_order_count"), ["Ayesha Khan", "Bilal Ahmed", "Che Lee"]
        )

    def test_list_query_count_does_not_grow_with_rows(self):
        def count_queries():
            with CaptureQueriesContext(connection) as ctx:
                response = self.client.get("/api/v1/customers/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return len(ctx.captured_queries)

        baseline = count_queries()
        for index in range(5):
            customer = Customer.objects.create(store=self.store, name=f"Extra {index}")
            self._order(customer, f"ORD-X{index}", timezone.now())
        self.assertEqual(count_queries(), baseline)
