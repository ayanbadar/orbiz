from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.common.testing import create_active_store
from apps.products.models import Product
from apps.stores.models import Role, Store, StoreMembership

PASSWORD = "Orb1z-pass"
TEST_SETTINGS = dict(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    CELERY_TASK_ALWAYS_EAGER=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEBUG=True,
)


def make_user(email, **kwargs):
    return User.objects.create_user(email=email, password=PASSWORD, first_name=email.split("@")[0], **kwargs)


@override_settings(**TEST_SETTINGS)
class TeamTestCase(APITestCase):
    def setUp(self):
        self.admin = make_user("admin@example.com")
        self.store = create_active_store(user=self.admin, name="Acme")
        self.viewer_role = Role.objects.create(store=self.store, name="Viewer", permissions=["products.read"])
        self.editor_role = Role.objects.create(
            store=self.store, name="Editor", permissions=["products.read", "products.create", "products.update"]
        )
        self.staff = make_user("staff@example.com")
        StoreMembership.objects.create(store=self.store, user=self.staff, role=self.viewer_role)

        self.other_admin = make_user("rival@example.com")
        self.other_store = create_active_store(user=self.other_admin, name="Rival")
        self.other_staff = make_user("rivalstaff@example.com")
        StoreMembership.objects.create(store=self.other_store, user=self.other_staff, role=None)


class PermissionEnforcementTests(TeamTestCase):
    def test_read_only_role_can_list_but_not_write_products(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/v1/products/").status_code, 200)
        denied = self.client.post("/api/v1/products/", {"name": "X", "sku": "X1", "price": "1.00"}, format="json")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_role_without_resource_is_blocked(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/v1/orders/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get("/api/v1/customers/").status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_can_create_but_not_delete(self):
        StoreMembership.objects.filter(user=self.staff).update(role=self.editor_role)
        product = Product.objects.create(store=self.store, name="P", sku="P1", price="5.00")
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.patch(f"/api/v1/products/{product.id}/", {"name": "P2"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/v1/products/{product.id}/").status_code, status.HTTP_403_FORBIDDEN)

    def test_store_admin_has_everything(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/v1/orders/").status_code, 200)

    def test_role_change_takes_effect_immediately(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/v1/orders/").status_code, 403)
        self.viewer_role.permissions = ["orders.read"]
        self.viewer_role.save()
        self.assertEqual(self.client.get("/api/v1/orders/").status_code, 200)


class StoreStateGateTests(TeamTestCase):
    def test_suspended_store_blocks_staff_with_valid_token(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/v1/products/").status_code, 200)
        Store.objects.filter(pk=self.store.pk).update(status=Store.Status.SUSPENDED)
        response = self.client.get("/api/v1/products/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "store_suspended")

    def test_unpaid_store_returns_payment_required(self):
        Store.objects.filter(pk=self.store.pk).update(status=Store.Status.PENDING_PAYMENT)
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/v1/products/")
        self.assertEqual(response.status_code, 402)
        self.assertEqual(response.data["code"], "payment_required")

    def test_store_endpoint_still_reports_status_when_suspended(self):
        Store.objects.filter(pk=self.store.pk).update(status=Store.Status.SUSPENDED)
        self.client.force_authenticate(self.staff)
        me = self.client.get("/api/v1/stores/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["status"], "suspended")

    def test_deactivated_user_cannot_login(self):
        self.staff.is_active = False
        self.staff.save()
        response = self.client.post(
            "/api/v1/auth/login/", {"email": "staff@example.com", "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "account_deactivated")


class TeamUsersTests(TeamTestCase):
    def test_admin_lists_only_own_store_users(self):
        self.client.force_authenticate(self.admin)
        emails = {u["email"] for u in self.client.get("/api/v1/team/users/").data["results"]}
        self.assertEqual(emails, {"admin@example.com", "staff@example.com"})

    def test_staff_without_users_permission_cannot_list(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/v1/team/users/").status_code, 403)

    def test_admin_updates_deactivates_and_deletes_staff(self):
        self.client.force_authenticate(self.admin)
        url = f"/api/v1/team/users/{self.staff.id}/"
        changed = self.client.patch(url, {"role_id": self.editor_role.id, "first_name": "Sam"}, format="json")
        self.assertEqual(changed.data["role"]["name"], "Editor")
        self.assertEqual(changed.data["first_name"], "Sam")

        off = self.client.patch(url, {"is_active": False}, format="json")
        self.assertFalse(off.data["is_active"])
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.staff.pk).exists())

    def test_cannot_touch_other_store_users_self_or_admin(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f"/api/v1/team/users/{self.other_staff.id}/", {"is_active": False}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/team/users/{self.admin.id}/").status_code, 403)

    def test_staff_with_users_permission_cannot_escalate(self):
        role = Role.objects.create(store=self.store, name="Manager", permissions=["users.read", "users.update"])
        StoreMembership.objects.filter(user=self.staff).update(role=role)
        self.client.force_authenticate(self.staff)
        target = make_user("t@example.com")
        StoreMembership.objects.create(store=self.store, user=target, role=self.viewer_role)
        response = self.client.patch(
            f"/api/v1/team/users/{target.id}/", {"role_id": self.editor_role.id}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "role_too_powerful")
        # a role within their own permissions is fine
        lite = Role.objects.create(store=self.store, name="Lite", permissions=["users.read"])
        ok = self.client.patch(f"/api/v1/team/users/{target.id}/", {"role_id": lite.id}, format="json")
        self.assertEqual(ok.status_code, 200)


class RoleTests(TeamTestCase):
    def test_admin_creates_updates_role_and_catalog_validated(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/v1/team/roles/",
            {"name": "Packer", "permissions": ["orders.read", "orders.update"]},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        bad = self.client.post("/api/v1/team/roles/", {"name": "Bad", "permissions": ["nope.read"]}, format="json")
        self.assertEqual(bad.status_code, 400)
        dup = self.client.post("/api/v1/team/roles/", {"name": "packer", "permissions": []}, format="json")
        self.assertEqual(dup.status_code, 400)
        patched = self.client.patch(f"/api/v1/team/roles/{created.data['id']}/", {"permissions": ["orders.read"]}, format="json")
        self.assertEqual(patched.data["permissions"], ["orders.read"])

    def test_role_in_use_cannot_be_deleted(self):
        self.client.force_authenticate(self.admin)
        blocked = self.client.delete(f"/api/v1/team/roles/{self.viewer_role.id}/")
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.data["code"], "role_in_use")
        free = self.client.delete(f"/api/v1/team/roles/{self.editor_role.id}/")
        self.assertEqual(free.status_code, 204)

    def test_non_admin_cannot_write_roles(self):
        role = Role.objects.create(store=self.store, name="Mgr", permissions=["users.read", "users.create", "users.update", "users.delete"])
        StoreMembership.objects.filter(user=self.staff).update(role=role)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get("/api/v1/team/roles/").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/team/roles/", {"name": "Z", "permissions": []}, format="json").status_code, 403)

    def test_roles_are_store_scoped(self):
        self.client.force_authenticate(self.other_admin)
        names = {r["name"] for r in self.client.get("/api/v1/team/roles/").data}
        self.assertNotIn("Viewer", names)
        self.assertEqual(self.client.delete(f"/api/v1/team/roles/{self.viewer_role.id}/").status_code, 404)
