import re

from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.services import FORGOT_PASSWORD_MESSAGE
from apps.notifications.models import EmailLog, EmailStatus

PASSWORD = "Orb1z-pass"
NEW_PASSWORD = "N3w-orbiz-pass"

TEST_SETTINGS = dict(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    DEBUG=False,
    FRONTEND_URL="http://localhost:5173",
    DEFAULT_FROM_EMAIL="Orbiz <noreply@orbiz.local>",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)


@override_settings(**TEST_SETTINGS)
class AuthApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="seller@example.com",
            password=PASSWORD,
            first_name="Aya",
            last_name="Khan",
        )

    def test_register_returns_tokens_and_profile(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "email": "New.Seller@example.com",
                "password": PASSWORD,
                "password_confirm": PASSWORD,
                "first_name": "Noor",
                "last_name": "Ali",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["email"], "new.seller@example.com")
        self.assertTrue(response.data["access"])
        self.assertTrue(response.data["refresh"])
        self.assertTrue(User.objects.filter(email="new.seller@example.com").exists())

    def test_register_rejects_duplicate_email_and_mismatched_passwords(self):
        duplicate = self.client.post(
            "/api/v1/auth/register/",
            {
                "email": "seller@example.com",
                "password": PASSWORD,
                "password_confirm": PASSWORD,
                "first_name": "Aya",
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", duplicate.data)

        mismatch = self.client.post(
            "/api/v1/auth/register/",
            {
                "email": "other@example.com",
                "password": PASSWORD,
                "password_confirm": "different-pass",
                "first_name": "Noor",
            },
            format="json",
        )
        self.assertEqual(mismatch.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", mismatch.data)

    def test_login_and_bad_password(self):
        ok = self.client.post(
            "/api/v1/auth/login/",
            {"email": "Seller@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertEqual(ok.data["user"]["first_name"], "Aya")

        bad = self.client.post(
            "/api/v1/auth/login/",
            {"email": "seller@example.com", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(bad.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(bad.data["detail"], "Invalid email or password.")

    def test_me_requires_auth_and_updates_profile(self):
        anonymous = self.client.get("/api/v1/auth/me/")
        self.assertEqual(anonymous.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(self.user)
        current = self.client.get("/api/v1/auth/me/")
        self.assertEqual(current.status_code, status.HTTP_200_OK)
        self.assertEqual(current.data["email"], "seller@example.com")

        updated = self.client.patch(
            "/api/v1/auth/me/",
            {"first_name": "Ayesha", "email": "hijack@example.com"},
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["first_name"], "Ayesha")
        self.assertEqual(updated.data["email"], "seller@example.com")

    def test_change_password_replaces_credentials(self):
        self.client.force_authenticate(self.user)
        wrong = self.client.post(
            "/api/v1/auth/change-password/",
            {
                "current_password": "not-the-password",
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(wrong.status_code, status.HTTP_400_BAD_REQUEST)

        changed = self.client.post(
            "/api/v1/auth/change-password/",
            {
                "current_password": PASSWORD,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(changed.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password(PASSWORD))
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

        self.client.force_authenticate(user=None)
        old_login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "seller@example.com", "password": PASSWORD},
            format="json",
        )
        new_login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "seller@example.com", "password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(old_login.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)

    def test_logout_blacklists_refresh_token(self):
        login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "seller@example.com", "password": PASSWORD},
            format="json",
        )
        access = login.data["access"]
        refresh = login.data["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        logout = self.client.post("/api/v1/auth/logout/", {"refresh": refresh}, format="json")
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)

        self.client.credentials()
        reused = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(reused.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_forgot_password_is_generic_and_reset_works(self):
        missing = self.client.post(
            "/api/v1/auth/forgot-password/",
            {"email": "missing@example.com"},
            format="json",
        )
        self.assertEqual(missing.status_code, status.HTTP_200_OK)
        self.assertEqual(missing.data["message"], FORGOT_PASSWORD_MESSAGE)
        self.assertNotIn("debug_reset_url", missing.data)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(EmailLog.objects.count(), 0)

        with self.captureOnCommitCallbacks(execute=True):
            sent = self.client.post(
                "/api/v1/auth/forgot-password/",
                {"email": "seller@example.com"},
                format="json",
            )
        self.assertEqual(sent.status_code, status.HTTP_200_OK)
        self.assertNotIn("debug_reset_url", sent.data)
        self.assertEqual(len(mail.outbox), 1)
        log = EmailLog.objects.get()
        self.assertEqual(log.kind, "password_reset")
        self.assertEqual(log.recipient, "seller@example.com")
        self.assertEqual(log.status, EmailStatus.SENT)

        match = re.search(r"uid=([^&\s]+)&token=([^\s]+)", mail.outbox[0].body)
        self.assertIsNotNone(match)
        uid, token = match.group(1), match.group(2)

        reset = self.client.post(
            "/api/v1/auth/reset-password/",
            {
                "uid": uid,
                "token": token,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(reset.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

        reused = self.client.post(
            "/api/v1/auth/reset-password/",
            {
                "uid": uid,
                "token": token,
                "new_password": "An0ther-pass",
                "new_password_confirm": "An0ther-pass",
            },
            format="json",
        )
        self.assertEqual(reused.status_code, status.HTTP_400_BAD_REQUEST)

    def test_debug_reset_url_is_only_returned_in_debug(self):
        with override_settings(DEBUG=True):
            response = self.client.post(
                "/api/v1/auth/forgot-password/",
                {"email": "seller@example.com"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/reset-password?uid=", response.data["debug_reset_url"])

    def test_login_is_rate_limited(self):
        from rest_framework.settings import api_settings
        from rest_framework.throttling import SimpleRateThrottle

        with override_settings(REST_FRAMEWORK=self._rest_framework_with_auth_limit("1/minute")):
            api_settings.reload()
            SimpleRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
            first = self.client.post(
                "/api/v1/auth/login/",
                {"email": "seller@example.com", "password": "wrong-password"},
                format="json",
            )
            second = self.client.post(
                "/api/v1/auth/login/",
                {"email": "seller@example.com", "password": "wrong-password"},
                format="json",
            )
        api_settings.reload()
        SimpleRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
        self.assertEqual(first.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_health_is_public_and_schema_requires_auth_outside_debug(self):
        health = self.client.get("/health/")
        self.assertEqual(health.status_code, status.HTTP_200_OK)

        schema = self.client.get("/api/schema/", HTTP_ACCEPT="application/json")
        docs = self.client.get("/api/docs/")
        self.assertEqual(schema.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(docs.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(self.user)
        schema_auth = self.client.get("/api/schema/", HTTP_ACCEPT="application/json")
        self.assertEqual(schema_auth.status_code, status.HTTP_200_OK)
        self.assertIn(b"/api/v1/auth/login/", schema_auth.content)

    @override_settings(DEBUG=True)
    def test_schema_is_public_when_debug(self):
        schema = self.client.get("/api/schema/", HTTP_ACCEPT="application/json")
        docs = self.client.get("/api/docs/")
        self.assertEqual(schema.status_code, status.HTTP_200_OK)
        self.assertEqual(docs.status_code, status.HTTP_200_OK)

    def test_logout_rejects_another_users_refresh_token(self):
        other = User.objects.create_user(email="other@example.com", password=PASSWORD, first_name="Other")
        other_refresh = str(RefreshToken.for_user(other))
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/auth/logout/",
            {"refresh": other_refresh},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def _rest_framework_with_auth_limit(self, rate: str) -> dict:
        from django.conf import settings

        config = {**settings.REST_FRAMEWORK}
        config["DEFAULT_THROTTLE_RATES"] = {
            **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
            "auth": rate,
        }
        return config
