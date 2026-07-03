from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1","192.168.11.47"]),
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

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "192.168.11.47",
]
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# -----------------------------
# DATABASE (SAFE FALLBACK)
# -----------------------------
DATABASE_URL = env("DATABASE_URL", default="").strip()

if DATABASE_URL:
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    # SAFE FALLBACK → SQLite
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

    # ⚠️ IMPORTANT:
    # DO NOT add "ratelimit" here
    # it is NOT a Django app
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

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

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
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

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

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1
CSRF_TRUSTED_ORIGINS = [
    "http://192.168.11.47:8000",
]