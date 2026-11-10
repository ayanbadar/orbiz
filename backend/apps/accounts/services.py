from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.accounts.models import User
from apps.notifications.services import queue_email

FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for that email, we sent reset instructions."
)
INVALID_CREDENTIALS_MESSAGE = "Invalid email or password."
INVALID_RESET_MESSAGE = "This reset link is invalid or has expired."


class InvalidResetLink(Exception):
    pass


def issue_tokens(user: User) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def blacklist_refresh_tokens(user: User) -> None:
    outstanding = OutstandingToken.objects.filter(user=user)
    for token in outstanding:
        BlacklistedToken.objects.get_or_create(token=token)


def build_password_reset_url(user: User) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    frontend = settings.FRONTEND_URL.rstrip("/")
    return f"{frontend}/reset-password?uid={uid}&token={token}"


def send_password_reset_email(user: User) -> str:
    reset_url = build_password_reset_url(user)
    queue_email(
        to=user.email,
        subject="Reset your Orbiz password",
        body=(
            "Use the link below to choose a new Orbiz password.\n\n"
            f"{reset_url}\n\n"
            "If you did not ask for this, you can ignore this email."
        ),
        kind="password_reset",
    )
    return reset_url


def get_user_for_reset(uid: str, token: str) -> User:
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError) as exc:
        raise InvalidResetLink from exc
    if not default_token_generator.check_token(user, token):
        raise InvalidResetLink
    return user
