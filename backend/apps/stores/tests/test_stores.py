from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.stores.models import StoreMembership
from apps.stores.services import create_store_for_user

PASSWORD = "Orb1z-pass"

TEST_SETTINGS = dict(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)


@override_settings(**TEST_SETTINGS)
class StoreApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password=PASSWORD,
            first_name="Owner",
        )
        self.other = User.objects.create_user(
            email="other@example.com",
            password=PASSWORD,
            first_name="Other",
        )

    def test_create_store_and_list(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/stores/",
            {
                "name": " Clifton Hoodies ",
                "currency": "usd",
                "timezone": "Asia/Karachi",
                "business_type": "social",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Clifton Hoodies")
        self.assertEqual(response.data["currency"], "USD")
        self.assertTrue(response.data["is_default"])
        self.assertEqual(response.data["role"], "owner")

        listed = self.client.get("/api/v1/stores/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertIn("results", listed.data)
        self.assertEqual(len(listed.data["results"]), 1)

        me = self.client.get("/api/v1/stores/me/")
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["id"], response.data["id"])

    def test_other_user_cannot_see_store(self):
        self.client.force_authenticate(self.user)
        created = self.client.post(
            "/api/v1/stores/",
            {"name": "Only Mine", "currency": "USD", "timezone": "UTC", "business_type": "social"},
            format="json",
        )
        store_id = created.data["id"]

        self.client.force_authenticate(self.other)
        detail = self.client.get(f"/api/v1/stores/{store_id}/")
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_set_default_switches(self):
        self.client.force_authenticate(self.user)
        first = self.client.post(
            "/api/v1/stores/",
            {"name": "One", "currency": "USD", "timezone": "UTC", "business_type": "social"},
            format="json",
        ).data
        second = self.client.post(
            "/api/v1/stores/",
            {"name": "Two", "currency": "USD", "timezone": "UTC", "business_type": "social"},
            format="json",
        ).data
        self.assertTrue(first["is_default"])
        self.assertFalse(second["is_default"])

        switched = self.client.post("/api/v1/stores/set-default/", {"store_id": second["id"]}, format="json")
        self.assertEqual(switched.status_code, status.HTTP_200_OK)
        self.assertTrue(switched.data["is_default"])
        self.assertEqual(
            StoreMembership.objects.filter(user=self.user, is_default=True).count(),
            1,
        )

    def test_member_cannot_patch_store(self):
        store = create_store_for_user(
            user=self.user,
            name="Owned",
            currency="USD",
            timezone="UTC",
            business_type="social",
        )
        StoreMembership.objects.create(
            store=store,
            user=self.other,
            role=StoreMembership.Role.MEMBER,
            is_default=True,
        )
        self.client.force_authenticate(self.other)
        response = self.client.patch(
            f"/api/v1/stores/{store.id}/",
            {"name": "Hijacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        store.refresh_from_db()
        self.assertEqual(store.name, "Owned")
