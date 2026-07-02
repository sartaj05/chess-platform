from __future__ import annotations
from datetime import timedelta
from pathlib import Path
import environ
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env(DJANGO_DEBUG=(bool, False), DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]), CSRF_TRUSTED_ORIGINS=(list, []), CORS_ALLOWED_ORIGINS=(list, []))
env_file = BASE_DIR / ".env"
if env_file.exists(): environ.Env.read_env(env_file)
SECRET_KEY = env("DJANGO_SECRET_KEY", default="local-development-key-change-before-production")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
DJANGO_APPS = ["django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "django.contrib.sites"]
THIRD_PARTY_APPS = ["corsheaders", "django_htmx", "channels", "rest_framework", "drf_spectacular", "allauth", "allauth.account", "allauth.socialaccount", "allauth.socialaccount.providers.google", "allauth.socialaccount.providers.github"]
LOCAL_APPS = ["apps.core", "apps.accounts", "apps.users", "apps.games", "apps.rooms", "apps.friends", "apps.chat", "apps.analysis", "apps.stockfish", "apps.puzzles", "apps.tournaments", "apps.notifications", "apps.payments", "apps.dashboard", "apps.blog", "apps.cms", "apps.api"]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "corsheaders.middleware.CorsMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "allauth.account.middleware.AccountMiddleware", "apps.accounts.middleware.UserActivityMiddleware", "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware", "django_htmx.middleware.HtmxMiddleware"]
ROOT_URLCONF = "chess_platform.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.debug", "django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages", "apps.core.context_processors.site_context"]}}]
WSGI_APPLICATION = "chess_platform.wsgi.application"
ASGI_APPLICATION = "chess_platform.asgi.application"
DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend", "allauth.account.auth_backends.AuthenticationBackend"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher", "django.contrib.auth.hashers.PBKDF2PasswordHasher", "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher"]
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}, {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}}, {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}, {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}, "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
SITE_ID = 1
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "core:home"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_RATE_LIMITS = {"login_failed": "5/m", "signup": "10/h"}
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "optional"
SOCIALACCOUNT_PROVIDERS = {"google": {"SCOPE": ["profile", "email"], "AUTH_PARAMS": {"access_type": "online"}, "OAUTH_PKCE_ENABLED": True}, "github": {"SCOPE": ["user", "user:email"]}}
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Chess Platform <noreply@localhost>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CHANNEL_REDIS_URL = env("CHANNEL_REDIS_URL", default="redis://localhost:6379/1")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/2")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/3")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 1800
CELERY_TASK_SOFT_TIME_LIMIT = 1500
CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL, "TIMEOUT": 300}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer", "CONFIG": {"hosts": [CHANNEL_REDIS_URL]}}}
REST_FRAMEWORK = {"DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication", "rest_framework.authentication.SessionAuthentication"), "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",), "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema", "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination", "PAGE_SIZE": 20}
SIMPLE_JWT = {"ACCESS_TOKEN_LIFETIME": timedelta(minutes=15), "REFRESH_TOKEN_LIFETIME": timedelta(days=14), "ROTATE_REFRESH_TOKENS": True, "BLACKLIST_AFTER_ROTATION": False, "UPDATE_LAST_LOGIN": True}
SPECTACULAR_SETTINGS = {"TITLE": "Chess Platform API", "DESCRIPTION": "REST API foundation for web and future mobile clients.", "VERSION": "1.0.0-module1", "SERVE_INCLUDE_SCHEMA": False}
OTP_CODE_TTL_MINUTES = 10
MAX_OTP_ATTEMPTS = 5
USER_ACTIVITY_CACHE_TTL = 180
