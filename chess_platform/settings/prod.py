from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

if SECRET_KEY == "dev-secret-key" or len(SECRET_KEY) < 50:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be a strong production secret.")
if not DATABASE_URL:  # noqa: F405
    raise ImproperlyConfigured("DATABASE_URL is required in production.")
if not REDIS_URL:  # noqa: F405
    raise ImproperlyConfigured("REDIS_URL is required in production.")

EMAIL_BACKEND = env(  # noqa: F405
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)  # noqa: F405
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)  # noqa: F405
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
