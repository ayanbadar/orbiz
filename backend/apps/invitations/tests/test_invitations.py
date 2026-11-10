from datetime import timedelta

from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.common.testing import create_active_store
from apps.invitations.models import Invitation
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
class InvitationTestCase(APITestCase):
    def setUp(self):
        self.root = make_user("root@example.com", is_superuser=True)
        self.admin = make_user("admin@example.com")
        self.store = create_active_store(user=self.admin, name="Acme")
        self.viewer = Role.objects.create(store=self.store, name="Viewer", permissions=["products.read"])
        self.editor = Role.objects.create(
            store=self.store, name="Editor", permissions=["products.read", "products.update"]
        )
        self.other_admin = make_user("rival@example.com")
        self.other_store = create_active_store(user=self.other_admin, name="Rival")


class StaffInvitationTests(InvitationTestCase):
    def accept(self, token, **extra):
        return self.client.post(
            f"/api/v1/invitations/{token}/accept/",
            {"first_name": "Nina", "password": PASSWORD, "password_confirm": PASSWORD, **extra},
            format="json",
        )

    def test_invite_sends_email_and_accept_creates_staff(self):
        self.client.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/invitations/", {"email": "New@Example.com", "role_id": self.editor.id}, format="json"
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accept-invite?token=", mail.outbox[0].body)
        token = Invitation.objects.get().token

        self.client.force_authenticate(None)
        preview = self.client.get(f"/api/v1/invitations/{token}/")
        self.assertEqual(preview.data["store_name"], "Acme")
        self.assertEqual(preview.data["role_name"], "Editor")

        accepted = self.accept(token)
        self.assertEqual(accepted.status_code, 201)
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.membership.role, self.editor)
        self.assertFalse(user.membership.is_store_admin)
        # Single use.
        self.assertEqual(self.accept(token).status_code, 404)

    def test_expired_invitation_rejected(self):
        invite = Invitation.objects.create(
            email="late@example.com", token="tok", kind="staff", store=self.store, role=self.viewer,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertEqual(self.client.get(f"/api/v1/invitations/{invite.token}/").status_code, 404)
        self.assertEqual(self.accept(invite.token).status_code, 404)

    def test_cannot_invite_with_another_stores_role(self):
        foreign = Role.objects.create(store=self.other_store, name="Foreign", permissions=[])
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/v1/invitations/", {"email": "x@example.com", "role_id": foreign.id}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_invite_existing_account(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/v1/invitations/", {"email": "rival@example.com", "role_id": self.viewer.id}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "email_taken")

    def test_reinviting_replaces_the_old_link(self):
        self.client.force_authenticate(self.admin)
        body = {"email": "dup@example.com", "role_id": self.viewer.id}
        first = Invitation.objects.get(pk=self.client.post("/api/v1/invitations/", body, format="json").data["id"])
        self.client.post("/api/v1/invitations/", body, format="json")
        self.assertEqual(Invitation.objects.filter(email="dup@example.com").count(), 1)
        self.assertFalse(Invitation.objects.filter(token=first.token).exists())

    def test_list_and_revoke_are_store_scoped(self):
        mine = Invitation.objects.create(
            email="a@example.com", token="t1", kind="staff", store=self.store, role=self.viewer,
            expires_at=timezone.now() + timedelta(days=1),
        )
        Invitation.objects.create(
            email="b@example.com", token="t2", kind="staff", store=self.other_store,
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.client.force_authenticate(self.admin)
        listed = self.client.get("/api/v1/invitations/")
        self.assertEqual([i["email"] for i in listed.data], ["a@example.com"])
        self.assertEqual(self.client.delete(f"/api/v1/invitations/{mine.id}/").status_code, 204)

        self.client.force_authenticate(self.other_admin)
        self.assertEqual(self.client.delete(f"/api/v1/invitations/{mine.id}/").status_code, 404)

    def test_staff_without_users_permission_cannot_invite(self):
        staff = make_user("staff@example.com")
        StoreMembership.objects.create(store=self.store, user=staff, role=self.viewer)
        self.client.force_authenticate(staff)
        response = self.client.post(
            "/api/v1/invitations/", {"email": "x@example.com", "role_id": self.viewer.id}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_manager_cannot_grant_a_stronger_role(self):
        manager_role = Role.objects.create(store=self.store, name="Mgr", permissions=["users.read", "users.create"])
        manager = make_user("mgr@example.com")
        StoreMembership.objects.create(store=self.store, user=manager, role=manager_role)
        self.client.force_authenticate(manager)
        response = self.client.post(
            "/api/v1/invitations/", {"email": "x@example.com", "role_id": self.editor.id}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "role_too_powerful")


class StoreAdminInvitationTests(InvitationTestCase):
    def test_platform_admin_invites_store_admin_who_gets_an_unpaid_store(self):
        self.client.force_authenticate(self.root)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.post(
                "/api/v1/invitations/store-admins/",
                {"email": "new@example.com", "store_name": "Gamma"},
                format="json",
            )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        token = Invitation.objects.get(email="new@example.com").token

        self.client.force_authenticate(None)
        accepted = self.client.post(
            f"/api/v1/invitations/{token}/accept/",
            {"first_name": "Gus", "password": PASSWORD, "password_confirm": PASSWORD},
            format="json",
        )
        self.assertEqual(accepted.status_code, 201)
        gamma = Store.objects.get(name="Gamma")
        self.assertEqual(gamma.status, Store.Status.PENDING_PAYMENT)
        self.assertTrue(gamma.memberships.get().is_store_admin)

    def test_only_platform_admin_can_invite_store_admins(self):
        for who in (self.admin, None):
            self.client.force_authenticate(who)
            r = self.client.post(
                "/api/v1/invitations/store-admins/", {"email": "n@example.com", "store_name": "X"}, format="json"
            )
            self.assertIn(r.status_code, (401, 403))

    def test_list_and_revoke_store_admin_invitations(self):
        self.client.force_authenticate(self.root)
        created = self.client.post(
            "/api/v1/invitations/store-admins/", {"email": "n@example.com", "store_name": "X"}, format="json"
        )
        listed = self.client.get("/api/v1/invitations/store-admins/")
        self.assertEqual([i["email"] for i in listed.data], ["n@example.com"])
        self.assertEqual(
            self.client.delete(f"/api/v1/invitations/store-admins/{created.data['id']}/").status_code, 204
        )
