# Chess Platform

A full-stack chess platform with a Django/Channels website and API, a Flutter Android application, PostgreSQL, Redis, Celery, Stockfish, Nginx, Docker, and signed Android release builds.

## Current features

### Accounts and community

- Email registration, verification, login, logout, password reset, JWT refresh, TOTP two-factor authentication, and Google/GitHub social-login wiring.
- Player profiles, avatars, game history, friends, challenges, direct chat, blocking, reporting, notifications, themes, sounds, and public leaderboards.
- Firebase Cloud Messaging device registration and push-delivery worker.

### Chess gameplay

- Same-device games, Stockfish bot games with progressive levels, private friend-code rooms, LAN play, public rooms, spectators, and online WebSocket gameplay.
- Server-authoritative legal moves, clocks, reconnect handling, abandonment results, resign/abort, draw offers, threefold/50-move claims, promotion selection, premoves, takebacks, rematches, PGN/FEN, replay, and game/spectator chat.
- Bullet, blitz, rapid, classical, and daily time categories with separate bullet/blitz/rapid Elo ratings.
- Rated matchmaking whose Elo range expands with queue waiting time.
- Tournaments, pairings, standings, and mobile tournament participation.

### Training and analysis

- Visual puzzles, daily puzzle, puzzle rating, streaks, best streak, and puzzle leaderboard.
- Stockfish bot moves and asynchronous post-game review using Celery.
- Move classifications, best lines, centipawn loss, White/Black accuracy, evaluation graph data, and failed-job retry.
- Opening explorer and personal opening statistics by ECO.
- Engine-assisted fair-play signals, risk scoring, moderator decisions, and audit notes. Fair-play flags never ban a player automatically.

### Flutter Android app

- Securely persisted access/refresh tokens and automatic refresh.
- Offline and online boards, matchmaking, profiles, history/replay, analysis, visual puzzles, leaderboards, openings, tournaments, friends, challenges, chat, notifications, themes, and sounds.
- Signed APK and Play Store AAB support using a protected local keystore.

## Architecture

| Component | Purpose |
|---|---|
| Django 5.2 / DRF | Website, REST API, authentication, business logic |
| Django Channels / Daphne | WebSocket rooms and live games |
| PostgreSQL | Production database |
| Redis | Channels, caching, Celery broker/results |
| Celery worker/beat | Analysis, push delivery, timeouts, abandonment, cleanup |
| Stockfish | Bot play, game analysis, and fair-play review signals |
| Flutter | Android application |
| Nginx / Gunicorn ASGI | Production reverse proxy and application server |

## Prerequisites

- Python 3.11 or newer (Python 3.13 recommended)
- Flutter stable and Android Studio/Android SDK for Android development
- Stockfish for bot play and analysis
- Redis for WebSockets and background jobs outside the Docker stack
- Docker Desktop for the recommended PostgreSQL/Redis production stack

## First-time Windows setup

From PowerShell in the repository root:

```powershell
.\scripts\setup_windows.ps1
```

The script creates `.env`, creates or reuses `.venv`/`venv`, installs Python dependencies, applies migrations, runs Django checks, restores Flutter packages, and runs `flutter doctor`.

To set up only the website:

```powershell
.\scripts\setup_windows.ps1 -SkipMobile
```

Manual setup is also supported:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

Website URLs:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/admin/`
- `http://127.0.0.1:8000/api/docs/`
- `http://127.0.0.1:8000/health/`

## Running locally

Run the website and apply pending migrations/checks automatically:

```powershell
.\scripts\run_local.ps1
```

Run the website plus Flutter on the Android emulator:

```powershell
.\scripts\run_local.ps1 -Mobile -ServerUrl "http://10.0.2.2:8000"
```

Use `10.0.2.2` only for the Android emulator. For a physical phone, connect both devices to the same network, find the computer's LAN IP, add it to `DJANGO_ALLOWED_HOSTS` in `.env`, and run:

```powershell
.\scripts\run_local.ps1 -Mobile -ServerUrl "http://192.168.1.10:8000"
```

If Django reports `Invalid HTTP_HOST header`, add the requested host (for example `10.0.2.2`) to `DJANGO_ALLOWED_HOSTS`, then restart Django.

## Offline local operation

The website does not load fonts, JavaScript, CSS, icons, or chess engines from
the internet at runtime. Bootstrap, HTMX, Alpine, the favicon, and Stockfish are
served locally. With Django running on the PC, bot games and same-device games
work without an internet connection. LAN games also work without internet when
the devices can reach the PC over the same Wi-Fi/router. Public internet is
only required for remote online play, social login, Firebase delivery, package
installation, and Play Store publishing.

## Redis, Celery, and background behavior

Production must run both worker and beat processes. They handle Stockfish reviews, Firebase push delivery, clock timeouts, reconnect grace periods, abandoned games, fair-play analysis, and cleanup.

```powershell
celery -A chess_platform worker -l info
celery -A chess_platform beat -l info
```

The Docker Compose stack starts these services automatically.

## Stockfish

Set `STOCKFISH_BINARY` in `.env`. Example Windows value:

```dotenv
STOCKFISH_BINARY=C:/stockfish/stockfish-windows-x86-64-avx2.exe
```

The production image installs Stockfish at `/usr/games/stockfish`. Restart Django and the Celery worker after changing engine settings.

## Database migrations

After pulling or copying updated source, always run:

```powershell
python manage.py migrate
python manage.py check
```

To remove Python cache files and run `makemigrations`, `migrate`, and `check`:

```powershell
.\venv\Scripts\python.exe .\scripts\migrations_cleanup.py
```

Migration files are preserved by default. Do not use the destructive migration-reset option against production data.

## Tests and validation

```powershell
pytest -q
python manage.py check
python manage.py makemigrations --check --dry-run
Set-Location mobile_app
flutter analyze
flutter test
```

## Firebase push notifications

1. Create a Firebase project and Android app.
2. Store the Firebase Admin service account at `secrets/firebase-service-account.json` (ignored by Git).
3. Set `FIREBASE_CREDENTIALS_FILE` and `FIREBASE_CREDENTIALS_HOST_PATH` in `.env.production`.
4. Build Flutter with the Firebase client values:

```powershell
flutter build appbundle --release `
  --dart-define=CHESS_SERVER_URL=https://chess.your-domain.com `
  --dart-define=FIREBASE_API_KEY=... `
  --dart-define=FIREBASE_APP_ID=... `
  --dart-define=FIREBASE_PROJECT_ID=... `
  --dart-define=FIREBASE_SENDER_ID=...
```

Without Firebase values, the app remains usable but real push delivery is disabled.

## Signed Android releases

Generate/reuse the private release keystore and build both APK and AAB:

```powershell
.\scripts\build_signed_apk.ps1 `
  -StorePassword (Read-Host -AsSecureString "Store password") `
  -KeyPassword (Read-Host -AsSecureString "Key password") `
  -ServerUrl "https://chess.your-domain.com"
```

Outputs:

- `mobile_app/build/app/outputs/flutter-apk/app-release.apk`
- `mobile_app/build/app/outputs/bundle/release/app-release.aab`

The keystore, `key.properties`, and Windows DPAPI password backups are ignored by Git. Keep an encrypted off-device backup of the keystore and passwords. Losing the keystore prevents future Play Store updates under the same application identity.

Never publish an APK built with the placeholder `https://chess.example.com`.

## Docker and production deployment

Create and edit the production environment file:

```powershell
Copy-Item .env.production.example .env.production
```

Replace every `REPLACE`/`example.com` value, configure DNS and HTTPS, then deploy:

```powershell
.\scripts\deploy_production.ps1 -Build
```

Equivalent Docker command:

```powershell
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml up --build -d
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py check --deploy
```

Production includes PostgreSQL, Redis, Django ASGI, Celery worker/beat, Nginx, health checks, API rate limiting, secure cookies, HSTS, CSP, and restricted database/cache exposure. TLS must terminate at Nginx or an upstream reverse proxy/load balancer.

## Backups and restore

Create timestamped PostgreSQL and media backups:

```powershell
.\scripts\backup_production.ps1
```

Restore a PostgreSQL dump:

```powershell
.\scripts\restore_production.ps1 -DatabaseDump ".\backups\database-YYYYMMDD-HHMMSS.dump"
```

Schedule backups, copy them to encrypted off-site storage, define retention, and regularly test a complete restore. A backup that has never been restored is not verified.

## Security and moderation

- Keep `.env`, `.env.production`, Firebase JSON, signing keys, DPAPI files, and backups outside Git.
- Rotate Django, database, SMTP, OAuth, Firebase, and infrastructure secrets before launch.
- Use HTTPS only in production and review `/health/`, service logs, backup results, and dependency alerts.
- Fair-play risk scores are screening signals. A staff moderator must review evidence and explicitly confirm or dismiss a case.
- User reports, blocks, chat reports, removed messages, and fair-play reviews are available to staff through Django admin and protected APIs.

## Social login

Create Google/GitHub `SocialApp` records at `/admin/socialaccount/socialapp/`.

- Google callback: `/social/google/login/callback/`
- GitHub callback: `/social/github/login/callback/`

## Before public launch

- Replace the placeholder domain everywhere and deploy valid HTTPS/DNS.
- Configure real SMTP, OAuth, Firebase, PostgreSQL, Redis, and secrets.
- Run migrations and keep Celery worker/beat continuously active.
- Rebuild and verify the signed APK/AAB with the real production URL.
- Test web versus phone, phone versus phone, reconnect/abandonment, push notifications, payments-free account deletion/data export policies, backup restore, load, and moderation workflows.
- Add external uptime/error/log monitoring and publish privacy policy, terms, Play Store screenshots, and release notes.

Additional workflow and setup documents are in `project_documentation/`.
