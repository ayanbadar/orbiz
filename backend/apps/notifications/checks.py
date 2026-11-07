from django.conf import settings
from django.core.checks import Error, Warning, register

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@register()
def smtp_settings(app_configs, **kwargs):
    """Catch an SMTP setup that cannot send before a customer's email silently fails."""
    if "smtp" not in settings.EMAIL_BACKEND.lower():
        return []

    issues = []
    if settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL:
        issues.append(
            Error(
                "EMAIL_USE_TLS and EMAIL_USE_SSL are both true.",
                hint="Use TLS (STARTTLS) with port 587, or SSL with port 465 — not both.",
                id="notifications.E001",
            )
        )
    if not settings.EMAIL_HOST:
        issues.append(
            Warning(
                "EMAIL_BACKEND is SMTP but EMAIL_HOST is empty.",
                id="notifications.W001",
            )
        )
    elif settings.EMAIL_HOST not in _LOCAL_HOSTS and not (
        settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD
    ):
        issues.append(
            Warning(
                "SMTP host is remote but EMAIL_HOST_USER / EMAIL_HOST_PASSWORD are not both set.",
                hint="Most providers reject unauthenticated mail. Gmail needs an App Password.",
                id="notifications.W002",
            )
        )
    return issues
