# Chess Platform - Module 1

Production Django foundation for a Chess.com/Lichess-style platform.

Included: Python 3.13, Django 6.0, PostgreSQL, Redis, Channels, Celery worker, Celery Beat, Gunicorn ASGI, Nginx, email login, OTP email verification, password reset, TOTP 2FA, profile/avatar, Google/GitHub social login wiring, JWT API, OpenAPI docs, pytest, and GitHub Actions.

## Run

```bash
cp .env.example .env
docker compose up --build
```

Open: `http://localhost`, `http://localhost/admin/`, `http://localhost/api/docs/`, `http://localhost/health/`.

## Admin

```bash
docker compose exec web python manage.py createsuperuser
```

## Tests

```bash
docker compose exec web pytest
```

## Social login

Create SocialApp records in `/admin/socialaccount/socialapp/` for Google and GitHub. Callback paths are `/social/google/login/callback/` and `/social/github/login/callback/`.
