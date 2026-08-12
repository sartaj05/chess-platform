# Chess Platform - Module 1

Production Django foundation for a Chess.com/Lichess-style platform.

Included: Python 3.13, Django 6.0, PostgreSQL, Redis, Channels, Celery worker, Celery Beat, Gunicorn ASGI, Nginx, email login, OTP email verification, password reset, TOTP 2FA, profile/avatar, Google/GitHub social login wiring, JWT API, OpenAPI docs, pytest, and GitHub Actions.

## Run

```bash
cp .env.example .env
docker compose up --build
```

Open: `http://localhost`, `http://localhost/admin/`, `http://localhost/api/docs/`, `http://localhost/health/`.

For a local Python environment, use Python 3.13 and install `requirements.txt`.
That file points to the maintained development dependency set:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py runserver
```

On Windows, the included helper scripts provide the same setup and also support
the Flutter Android app:

```powershell
.\scripts\setup_windows.ps1
.\scripts\run_local.ps1
.\scripts\run_local.ps1 -Mobile
```

Use `.\scripts\run_local.ps1 -CheckOnly` to apply pending migrations and run
Django's system checks without starting a server. Project workflow, first-time
setup, and feature-status guides are available as Word documents in
`project_documentation/`.

To clean Python cache files and run `makemigrations`, `migrate`, and `check`:

```powershell
.\venv\Scripts\python.exe .\scripts\migrations_cleanup.py
```

Migration files are preserved by default. The exceptional
`--reset-migrations --yes` mode deletes generated migration files while keeping
each `migrations/__init__.py`; use it only with a backed-up development database.

## Admin

```bash
docker compose exec web python manage.py createsuperuser
```

## Tests

```bash
docker compose exec web pytest
```

## Production configuration

Copy `.env.production.example` to `.env.production`, replace every placeholder,
and deploy with both Compose files:

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml up --build -d
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py check --deploy
```

The production override removes public PostgreSQL/Redis ports and source-code
bind mounts. Terminate TLS at the reverse proxy or load balancer before enabling
the included HTTPS security settings.

## Social login

Create SocialApp records in `/admin/socialaccount/socialapp/` for Google and GitHub. Callback paths are `/social/google/login/callback/` and `/social/github/login/callback/`.


## Module 2: Rooms and Realtime Lobby

Module 2 adds production room creation, private invite URLs, join-by-code, LAN-mode room flow, room participants, room event logs, REST endpoints, WebSocket room chat, ready state, and reconnect-ready room state JSON. See `docs_module2_rooms.md`.


## Module 3 - Realtime Gameplay

Module 3 adds server-authoritative chess gameplay using python-chess, WebSocket move broadcasting, drag/drop board UI, clocks, FEN/PGN import/export, resign, abort, draw offer, captured pieces, move history, and REST game endpoints.

Useful URLs:

- `/games/same-pc/new/` - create offline same-computer game
- `/games/fen/import/` - import a FEN position
- `/games/<uuid>/` - play/watch a game
- `/api/games/` - game API list
- `/ws/games/<uuid>/` - realtime game WebSocket


## Module 4 - Stockfish Analysis

Adds offline Stockfish integration, analysis board, full-game review jobs, move classification, evaluation graph data, and seeded opening explorer. See `docs_module4_analysis.md`.
