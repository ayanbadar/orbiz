from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.common.testing import create_active_store
from apps.stores.models import Store
from apps.stores.services import create_store_for_user

PASSWORD = "Orb1z-pass"

TEST_SETTINGS = dict(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)


@override_settings(**TEST_SETTINGS)
class StoreApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password=PASSWORD, first_name="Owner")
        self.other = User.objects.create_user(email="other@example.com", password=PASSWORD, first_name="Other")

    def test_create_store_starts_unpaid_with_admin_membership(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/stores/",
            {"name": "Aya Boutique", "currency": "usd", "timezone": "Asia/Karachi", "business_type": "social"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "pending_payment")
        self.assertTrue(response.data["is_store_admin"])
        # 5 resources (products, orders, customers, users, assistant) × 4 actions each.
        self.assertEqual(len(response.data["permissions"]), 20)

        me = self.client.get("/api/v1/stores/me/")
        self.assertEqual(me.data["id"], response.data["id"])

    def test_user_cannot_create_a_second_store(self):
        create_store_for_user(user=self.user, name="First")
        self.client.force_authenticate(self.user)
        response = self.client.post("/api/v1/stores/", {"name": "Second"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_other_user_cannot_see_store(self):
        store = create_active_store(user=self.user)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/v1/stores/{store.id}/").status_code, status.HTTP_404_NOT_FOUND)

    def test_store_admin_can_patch_but_staff_cannot(self):
        from apps.stores.models import Role, StoreMembership

        store = create_active_store(user=self.user)
        role = Role.objects.create(store=store, name="Viewer", permissions=["products.read"])
        StoreMembership.objects.create(store=store, user=self.other, role=role)

        self.client.force_authenticate(self.user)
        ok = self.client.patch(f"/api/v1/stores/{store.id}/", {"name": "Renamed"}, format="json")
        self.assertEqual(ok.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.other)
        denied = self.client.patch(f"/api/v1/stores/{store.id}/", {"name": "Hacked"}, format="json")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Store.objects.get(pk=store.pk).name, "Renamed")
