from .base import *  # noqa: F403

DEBUG = False
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
