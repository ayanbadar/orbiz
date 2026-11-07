from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from apps.notifications.tasks import describe_failure


def mask_email(value: str) -> str:
    """ab***@example.com — enough to recognise the account, not to copy it."""
    address = value.rsplit("<", 1)[-1].strip(" >")
    local, _, domain = address.partition("@")
    if not domain:
        return "<set>" if value else "<missing>"
    return f"{local[:2]}***@{domain}"


class Command(BaseCommand):
    help = (
        "Send one email synchronously through the configured EMAIL_BACKEND to prove "
        "SMTP works. Run it in the celery_worker container too, since that is what sends."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            help="Inbox that should receive the test. Defaults to the SMTP login (a message to yourself).",
        )
        parser.add_argument("--subject", default="Orbiz SMTP test")

    def handle(self, *args, **options):
        recipient = (options["to"] or settings.EMAIL_HOST_USER or "").strip()
        if not recipient:
            raise CommandError("Pass --to; there is no SMTP login to default to.")
        try:
            validate_email(recipient)
        except ValidationError as exc:
            raise CommandError("--to is not a valid email address.") from exc

        backend = settings.EMAIL_BACKEND
        is_smtp = "smtp" in backend.lower()
        security = "SSL" if settings.EMAIL_USE_SSL else "STARTTLS" if settings.EMAIL_USE_TLS else "none"
        self.stdout.write(f"backend : {backend}")
        if is_smtp:
            self.stdout.write(f"server  : {settings.EMAIL_HOST}:{settings.EMAIL_PORT} ({security})")
            self.stdout.write(f"login   : {mask_email(settings.EMAIL_HOST_USER)}")
            self.stdout.write(
                f"password: {'<set>' if settings.EMAIL_HOST_PASSWORD else '<missing>'}"
            )
        self.stdout.write(f"from    : {mask_email(settings.DEFAULT_FROM_EMAIL)}")
        self.stdout.write(f"to      : {mask_email(recipient)}")

        message = EmailMultiAlternatives(
            subject=options["subject"],
            body="This is a test email from Orbiz. If you can read it, SMTP delivery works.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        message.attach_alternative(
            "<p>This is a <strong>test email</strong> from Orbiz.</p>"
            "<p>If you can read it, SMTP delivery works.</p>",
            "text/html",
        )
        try:
            message.send(fail_silently=False)
        except Exception as exc:
            raise CommandError(f"Send failed — {describe_failure(exc)} ({type(exc).__name__})") from exc

        if is_smtp:
            self.stdout.write(self.style.SUCCESS("Accepted by the SMTP server. Check the inbox and spam."))
        else:
            self.stdout.write(
                self.style.WARNING(f"Backend {backend} does not deliver to a real inbox.")
            )
