from __future__ import annotations

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
)

# Load .env
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

# -----------------------------
# CORE SETTINGS
# -----------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-secret-key")
DEBUG = env("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = env(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "0.0.0.0", "web"],
)
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# -----------------------------
# DATABASE (SAFE FALLBACK)
# -----------------------------
DATABASE_URL = env("DATABASE_URL", default="").strip()

if DATABASE_URL:
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# -----------------------------
# APPS
# -----------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "django_htmx",
    "channels",
    "rest_framework",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.github",
]
LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.users",
    "apps.games",
    "apps.rooms",
    "apps.friends",
    "apps.chat",
    "apps.analysis",
    "apps.stockfish",
    "apps.puzzles",
    "apps.tournaments",
    "apps.notifications",
    "apps.payments",
    "apps.dashboard",
    "apps.blog",
    "apps.cms",
    "apps.api",
]

INSTALLED_APPS = ["daphne"] + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# -----------------------------
# MIDDLEWARE
# -----------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.accounts.middleware.UserActivityMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "chess_platform.urls"

# -----------------------------
# TEMPLATES
# -----------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_context",
            ],
        },
    }
]

WSGI_APPLICATION = "chess_platform.wsgi.application"
ASGI_APPLICATION = "chess_platform.asgi.application"

REDIS_URL = env("REDIS_URL", default="").strip()
CHANNEL_REDIS_URL = env("CHANNEL_REDIS_URL", default=REDIS_URL).strip()

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "chess-platform",
        }
    }

if CHANNEL_REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [CHANNEL_REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

# -----------------------------
# AUTH
# -----------------------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# -----------------------------
# ALLAUTH (FIXED CONFIG)
# -----------------------------
ACCOUNT_LOGIN_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False

ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True

ACCOUNT_RATE_LIMITS = {
    "login_failed": "5/m",
    "signup": "10/h",
}

SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "optional"

# NOTE: previously this dict was defined twice in the file — once with
# SCOPE/AUTH_PARAMS and again with APP credentials. The second definition
# silently overwrote the first (plain Python variable reassignment), so the
# scope/PKCE settings were being dropped. Merged into a single block below.
#
# Read the real client id/secret from your .env file rather than hardcoding
# them here. Add to .env:
#   GOOGLE_OAUTH_CLIENT_ID=...
#   GOOGLE_OAUTH_CLIENT_SECRET=...
#   GITHUB_OAUTH_CLIENT_ID=...
#   GITHUB_OAUTH_CLIENT_SECRET=...
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
        "APP": {
            "client_id": env("GOOGLE_OAUTH_CLIENT_ID", default="YOUR_GOOGLE_CLIENT_ID"),
            "secret": env("GOOGLE_OAUTH_CLIENT_SECRET", default="YOUR_GOOGLE_CLIENT_SECRET"),
            "key": "",
        },
    },
    "github": {
        "SCOPE": ["user", "user:email"],
        "APP": {
            "client_id": env("GITHUB_OAUTH_CLIENT_ID", default="YOUR_GITHUB_CLIENT_ID"),
            "secret": env("GITHUB_OAUTH_CLIENT_SECRET", default="YOUR_GITHUB_CLIENT_SECRET"),
            "key": "",
        },
    },
}

# -----------------------------
# REST FRAMEWORK
# -----------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "room_write_anon": env("API_THROTTLE_ROOM_WRITE_ANON", default="60/hour"),
        "room_write_user": env("API_THROTTLE_ROOM_WRITE_USER", default="180/hour"),
        "analysis_anon": env("API_THROTTLE_ANALYSIS_ANON", default="10/hour"),
        "analysis_user": env("API_THROTTLE_ANALYSIS_USER", default="60/hour"),
        "offline_sync": env("API_THROTTLE_OFFLINE_SYNC", default="120/hour"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Chess Platform API",
    "DESCRIPTION": "REST API for accounts, rooms, games, and chess analysis.",
    "VERSION": "1.0.0",
    "ENUM_NAME_OVERRIDES": {
        "ChessColorEnum": [("white", "White"), ("black", "Black")],
    },
}

# -----------------------------
# ACCOUNT SECURITY / EMAIL
# -----------------------------
# Keep these values available in every settings environment.  The account
# tasks read them directly when generating verification emails.
OTP_CODE_TTL_MINUTES = env.int("OTP_CODE_TTL_MINUTES", default=10)
MAX_OTP_ATTEMPTS = env.int("MAX_OTP_ATTEMPTS", default=5)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@chessplatform.local")
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
USER_ACTIVITY_CACHE_TTL = env.int("USER_ACTIVITY_CACHE_TTL", default=180)

# -----------------------------
# STATIC / MEDIA
# -----------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------
# TIME
# -----------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# -----------------------------
# BACKGROUND TASKS
# -----------------------------
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default=REDIS_URL or "memory://",
)
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default=REDIS_URL or "cache+memory://",
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1
