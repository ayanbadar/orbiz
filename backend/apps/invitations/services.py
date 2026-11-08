"""Every invite in the application goes through here (staff invites and store-admin invites)."""

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import ConflictError, NotFoundError
from apps.invitations.models import Invitation
from apps.notifications.services import queue_email
from apps.stores.models import Role, Store, StoreMembership
from apps.stores.services import create_store_for_user

INVITE_TTL_DAYS = 7
INVALID_INVITATION_MESSAGE = "This invitation is invalid or has expired."


def invitation_url(invitation: Invitation) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/accept-invite?token={invitation.token}"


@transaction.atomic
def create_invitation(
    *,
    invited_by,
    email: str,
    kind: str,
    store: Store | None = None,
    store_name: str = "",
    role: Role | None = None,
) -> Invitation:
    """Create (or replace) a pending invite and email the link."""
    email = email.strip().lower()
    if User.objects.filter(email__iexact=email).exists():
        raise ConflictError("An account with this email already exists.", code="email_taken")
    # One live invite per email: re-inviting replaces the old link.
    Invitation.objects.filter(email__iexact=email, accepted_at__isnull=True).delete()

    invitation = Invitation.objects.create(
        email=email,
        token=secrets.token_urlsafe(32),
        kind=kind,
        store=store,
        store_name=store_name,
        role=role,
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=INVITE_TTL_DAYS),
    )
    destination = store.name if store else store_name
    queue_email(
        to=email,
        subject=f"You're invited to {destination} on Orbiz",
        body=(
            f"You've been invited to join {destination} on Orbiz.\n\n"
            f"Accept the invitation and set your password:\n{invitation_url(invitation)}\n\n"
            f"This link expires in {INVITE_TTL_DAYS} days."
        ),
        kind="invitation",
    )
    return invitation


def pending_invitations():
    return Invitation.objects.filter(accepted_at__isnull=True, expires_at__gt=timezone.now())


def get_pending_invitation(token: str) -> Invitation:
    invitation = (
        Invitation.objects.select_related("store", "role").filter(token=token, accepted_at__isnull=True).first()
    )
    if invitation is None or invitation.expires_at < timezone.now():
        raise NotFoundError(INVALID_INVITATION_MESSAGE, code="invalid_invitation")
    return invitation


@transaction.atomic
def accept_invitation(*, token: str, first_name: str, last_name: str, password: str) -> User:
    """Create the account behind an invite. Store-admin invites also create the (unpaid) store."""
    invitation = get_pending_invitation(token)
    if User.objects.filter(email__iexact=invitation.email).exists():
        raise ConflictError("An account with this email already exists.", code="email_taken")

    user = User.objects.create_user(
        email=invitation.email, password=password, first_name=first_name, last_name=last_name
    )
    if invitation.kind == Invitation.Kind.STORE_ADMIN:
        create_store_for_user(user=user, name=invitation.store_name)
    else:
        StoreMembership.objects.create(store=invitation.store, user=user, role=invitation.role)
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at"])
    return user
