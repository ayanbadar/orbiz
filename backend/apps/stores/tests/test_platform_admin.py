from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.common.testing import create_active_store
from apps.stores.models import Role, Store, StoreMembership

PASSWORD = "Orb1z-pass"
TEST_SETTINGS = dict(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)


def user(email, **kw):
    return User.objects.create_user(email=email, password=PASSWORD, first_name=email.split("@")[0], **kw)


@override_settings(**TEST_SETTINGS)
class PlatformAdminTests(APITestCase):
    def setUp(self):
        self.root = user("root@example.com", is_superuser=True)
        self.admin_a = user("a@example.com")
        self.store_a = create_active_store(user=self.admin_a, name="Alpha")
        self.role = Role.objects.create(store=self.store_a, name="Viewer", permissions=["products.read"])
        self.staff_a = user("sa@example.com")
        StoreMembership.objects.create(store=self.store_a, user=self.staff_a, role=self.role)
        self.admin_b = user("b@example.com")
        self.store_b = create_active_store(user=self.admin_b, name="Beta")

    def test_only_platform_admin_can_use_admin_api(self):
        for who in (self.admin_a, self.staff_a):
            self.client.force_authenticate(who)
            self.assertEqual(self.client.get("/api/v1/admin/stores/").status_code, 403)
            self.assertEqual(self.client.get("/api/v1/admin/users/").status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/v1/admin/stores/").status_code, 401)

    def test_lists_all_stores_and_users(self):
        self.client.force_authenticate(self.root)
        stores = self.client.get("/api/v1/admin/stores/").data["results"]
        self.assertEqual({s["name"] for s in stores}, {"Alpha", "Beta"})
        alpha = next(s for s in stores if s["name"] == "Alpha")
        self.assertEqual(alpha["user_count"], 2)
        self.assertEqual(alpha["admin_email"], "a@example.com")

        users = self.client.get("/api/v1/admin/users/").data["results"]
        self.assertEqual({u["email"] for u in users}, {"a@example.com", "sa@example.com", "b@example.com"})
        scoped = self.client.get(f"/api/v1/admin/users/?store={self.store_a.id}").data["results"]
        self.assertEqual({u["email"] for u in scoped}, {"a@example.com", "sa@example.com"})

    def test_deactivating_store_admin_locks_out_whole_store(self):
        self.client.force_authenticate(self.staff_a)
        self.assertEqual(self.client.get("/api/v1/products/").status_code, 200)

        self.client.force_authenticate(self.root)
        off = self.client.patch(f"/api/v1/admin/users/{self.admin_a.id}/", {"is_active": False}, format="json")
        self.assertEqual(off.status_code, 200)
        self.assertFalse(off.data["is_active"])
        self.store_a.refresh_from_db()
        self.assertEqual(self.store_a.status, Store.Status.SUSPENDED)

        self.client.force_authenticate(self.staff_a)
        blocked = self.client.get("/api/v1/products/")
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.data["code"], "store_suspended")
        # Other stores are unaffected.
        self.client.force_authenticate(self.admin_b)
        self.assertEqual(self.client.get("/api/v1/products/").status_code, 200)

        # Reactivating restores access (subscription is still paid → active).
        self.client.force_authenticate(self.root)
        self.client.patch(f"/api/v1/admin/users/{self.admin_a.id}/", {"is_active": True}, format="json")
        self.client.force_authenticate(self.staff_a)
        self.assertEqual(self.client.get("/api/v1/products/").status_code, 200)

    def test_suspend_and_reactivate_store_directly(self):
        self.client.force_authenticate(self.root)
        url = f"/api/v1/admin/stores/{self.store_a.id}/"
        self.assertEqual(self.client.patch(url, {"suspended": True}, format="json").data["status"], "suspended")
        self.assertEqual(self.client.patch(url, {"suspended": False}, format="json").data["status"], "active")

    def test_delete_store_admin_removes_store_and_its_users(self):
        self.client.force_authenticate(self.root)
        self.assertEqual(self.client.delete(f"/api/v1/admin/users/{self.admin_a.id}/").status_code, 204)
        self.assertFalse(Store.objects.filter(pk=self.store_a.pk).exists())
        self.assertFalse(User.objects.filter(email__in=["a@example.com", "sa@example.com"]).exists())
        self.assertTrue(User.objects.filter(email="b@example.com").exists())

    def test_delete_store_removes_its_users(self):
        self.client.force_authenticate(self.root)
        self.assertEqual(self.client.delete(f"/api/v1/admin/stores/{self.store_b.id}/").status_code, 204)
        self.assertFalse(User.objects.filter(email="b@example.com").exists())

    def test_platform_admin_cannot_be_modified_via_api(self):
        self.client.force_authenticate(self.root)
        self.assertEqual(self.client.delete(f"/api/v1/admin/users/{self.root.id}/").status_code, 404)
