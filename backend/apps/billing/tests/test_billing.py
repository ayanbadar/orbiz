from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.billing.models import Payment, Subscription
from apps.billing.services import expire_subscriptions
from apps.stores.models import Role, Store, StoreMembership
from apps.stores.services import create_store_for_user

PASSWORD = "Orb1z-pass"
TEST_SETTINGS = dict(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    DEBUG=True,
)


@override_settings(**TEST_SETTINGS)
class BillingTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="a@example.com", password=PASSWORD, first_name="A")
        self.store = create_store_for_user(user=self.admin, name="Shop")  # starts pending_payment

    def test_unpaid_store_checkout_activates_it(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/v1/products/").status_code, 402)

        status_before = self.client.get("/api/v1/billing/")
        self.assertEqual(status_before.data["plan_price_cents"], 500)
        self.assertEqual(status_before.data["store_status"], "pending_payment")

        paid = self.client.post("/api/v1/billing/checkout/", {"card_number": "4242424242424242"}, format="json")
        self.assertEqual(paid.status_code, 201)
        self.assertEqual(paid.data["store_status"], "active")
        self.assertEqual(paid.data["payments"][0]["amount_cents"], 500)
        self.assertEqual(self.client.get("/api/v1/products/").status_code, 200)

    def test_failed_payment_leaves_store_unpaid(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/v1/billing/checkout/", {"simulate_failure": True}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "payment_failed")
        self.store.refresh_from_db()
        self.assertEqual(self.store.status, Store.Status.PENDING_PAYMENT)
        self.assertEqual(Payment.objects.get().status, Payment.Status.FAILED)

    def test_renewal_extends_period(self):
        self.client.force_authenticate(self.admin)
        self.client.post("/api/v1/billing/checkout/", {}, format="json")
        first_end = Subscription.objects.get(store=self.store).current_period_end
        self.client.post("/api/v1/billing/checkout/", {}, format="json")
        self.assertGreater(Subscription.objects.get(store=self.store).current_period_end, first_end + timedelta(days=29))

    def test_expiry_locks_store_until_paid_again(self):
        self.client.force_authenticate(self.admin)
        self.client.post("/api/v1/billing/checkout/", {}, format="json")
        Subscription.objects.filter(store=self.store).update(current_period_end=timezone.now() - timedelta(days=1))
        self.assertEqual(expire_subscriptions(), 1)
        self.assertEqual(self.client.get("/api/v1/products/").status_code, 402)
        self.client.post("/api/v1/billing/checkout/", {}, format="json")
        self.assertEqual(self.client.get("/api/v1/products/").status_code, 200)

    def test_cancel_keeps_access_until_period_ends(self):
        self.client.force_authenticate(self.admin)
        self.client.post("/api/v1/billing/checkout/", {}, format="json")
        cancelled = self.client.post("/api/v1/billing/cancel/")
        self.assertEqual(cancelled.data["subscription_status"], "canceled")
        self.assertEqual(self.client.get("/api/v1/products/").status_code, 200)

    def test_staff_cannot_use_billing(self):
        role = Role.objects.create(store=self.store, name="R", permissions=[])
        staff = User.objects.create_user(email="s@example.com", password=PASSWORD, first_name="S")
        StoreMembership.objects.create(store=self.store, user=staff, role=role)
        self.client.force_authenticate(staff)
        self.assertEqual(self.client.get("/api/v1/billing/").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/billing/checkout/", {}, format="json").status_code, 403)

    def test_suspended_store_cannot_pay_its_way_out(self):
        Store.objects.filter(pk=self.store.pk).update(status=Store.Status.SUSPENDED)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post("/api/v1/billing/checkout/", {}, format="json").status_code, 403)
