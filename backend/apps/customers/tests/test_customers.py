from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.customers.models import Customer
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
