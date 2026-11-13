"""
Single Django settings module. Environment-specific values come from .env / process env.
"""

from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    CORS_ALLOW_ALL_ORIGINS=(bool, False),
    FRONTEND_URL=(str, "http://localhost:5173"),
    EMAIL_BACKEND=(str, "django.core.mail.backends.console.EmailBackend"),
    EMAIL_HOST=(str, "localhost"),
    EMAIL_PORT=(int, 25),
    EMAIL_USE_TLS=(bool, False),
    EMAIL_USE_SSL=(bool, False),
    EMAIL_HOST_USER=(str, ""),
    EMAIL_HOST_PASSWORD=(str, ""),
    EMAIL_TIMEOUT=(int, 10),
    DEFAULT_FROM_EMAIL=(str, "Orbiz <noreply@orbiz.local>"),
    USE_LOCMEM_CACHE=(bool, False),
)

# Prefer backend/.env; root .env is injected by Compose into the process environment.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "apps.common",
    "apps.accounts",
    "apps.notifications",
    "apps.stores",
    "apps.invitations",
    "apps.billing",
    "apps.products",
    "apps.customers",
    "apps.orders",
    "apps.payments",
    "apps.dashboard",
    "apps.assistant",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}

if env.bool("USE_LOCMEM_CACHE"):
    # Local runs without Redis. Docker and deployed environments keep Redis.
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "orbiz",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": env("REDIS_URL"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS — use explicit origins from env; optionally allow all when DEBUG=True
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)
if DEBUG and not CORS_ALLOWED_ORIGINS and not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exception_handler.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
        "auth": "10/minute",
        "password": "5/minute",
        "writes": "60/minute",
        "channel3": "30/minute",
        "payments": "30/minute",
        "assistant": "30/minute",
    },
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Orbiz API",
    "DESCRIPTION": "Commerce operations API. Authentication uses Bearer access tokens.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [{"bearerAuth": []}],
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
    "TAGS": [
        {"name": "auth", "description": "Sign in, profile, and password management."},
        {"name": "stores", "description": "Store workspaces and membership."},
        {"name": "products", "description": "Catalog, inventory, and Channel3 enrichment."},
        {"name": "customers", "description": "Store customers linked to orders."},
        {"name": "orders", "description": "Draft and confirmed orders, stock, and status."},
        {"name": "payments", "description": "PayPal Sandbox checkout, capture, and webhooks."},
        {"name": "dashboard", "description": "Store and platform analytics summaries."},
        {"name": "assistant", "description": "Orbiz AI — chat, drafts, and proposed actions."},
    ],
}

FRONTEND_URL = env("FRONTEND_URL")
EMAIL_BACKEND = env("EMAIL_BACKEND")
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
# Short timeout so an unreachable SMTP server cannot hang a Celery worker.
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")

CHANNEL3_API_KEY = env("CHANNEL3_API_KEY", default="")
CHANNEL3_BASE_URL = env("CHANNEL3_BASE_URL", default="https://api.trychannel3.com")

# Orbiz AI (server-side only — never expose in VITE_*)
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_API_BASE = env("OPENAI_API_BASE", default="https://api.openai.com/v1")
ASSISTANT_MODEL = env("ASSISTANT_MODEL", default="gpt-5-mini")
# "low" keeps GPT-5-family tool-choice reasoning without "medium"'s latency; "minimal" is faster
# but trades away tool-choice accuracy. Empty string drops the field for non-reasoning models.
ASSISTANT_REASONING_EFFORT = env("ASSISTANT_REASONING_EFFORT", default="low")

# PayPal Sandbox (server-side only — never expose in VITE_*)
PAYPAL_CLIENT_ID = env("PAYPAL_CLIENT_ID", default="")
PAYPAL_CLIENT_SECRET = env("PAYPAL_CLIENT_SECRET", default="")
PAYPAL_MODE = env("PAYPAL_MODE", default="sandbox")
PAYPAL_WEBHOOK_ID = env("PAYPAL_WEBHOOK_ID", default="")
PAYPAL_API_BASE = env("PAYPAL_API_BASE", default="")
# Currencies the PayPal merchant can take (PKR is unsupported — Pakistan is not a PayPal country).
PAYPAL_SUPPORTED_CURRENCIES = [
    code.upper() for code in env.list("PAYPAL_SUPPORTED_CURRENCIES", default=["USD"])
]
# Who emails the buyer a payment request: "orbiz" sends it through our SMTP and creates the
# PayPal invoice link-only; "paypal" lets PayPal email its own invoice (Sandbox never delivers it).
PAYPAL_INVOICE_DELIVERY = env("PAYPAL_INVOICE_DELIVERY", default="orbiz").strip().lower()
if PAYPAL_INVOICE_DELIVERY not in {"orbiz", "paypal"}:
    raise ImproperlyConfigured("PAYPAL_INVOICE_DELIVERY must be 'orbiz' or 'paypal'.")
# A checkout link older than this is replaced by a fresh one before it is emailed.
PAYPAL_CHECKOUT_LINK_MAX_AGE_HOURS = env.int("PAYPAL_CHECKOUT_LINK_MAX_AGE_HOURS", default=24)
# Emailing the same address the same payment link again is refused for this long.
PAYMENT_EMAIL_COOLDOWN_SECONDS = env.int("PAYMENT_EMAIL_COOLDOWN_SECONDS", default=120)
# Tell the store's members by email when a PayPal payment lands.
NOTIFY_SELLER_ON_PAYMENT = env.bool("NOTIFY_SELLER_ON_PAYMENT", default=True)

# Celery (namespace CELERY_*)
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
# Run tasks inline (no broker/worker). For hosts without Redis/Celery, e.g. Render free tier.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BEAT_SCHEDULE = {
    "expire-subscriptions-daily": {
        "task": "apps.billing.tasks.expire_subscriptions_task",
        "schedule": 60 * 60 * 24,
    },
}
