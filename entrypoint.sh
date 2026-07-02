#!/usr/bin/env sh
set -eu
if [ -n "${DATABASE_URL:-}" ]; then
  DB_HOST=$(python -c 'import os; from urllib.parse import urlparse; u=urlparse(os.environ["DATABASE_URL"]); print(u.hostname or "db")')
  DB_PORT=$(python -c 'import os; from urllib.parse import urlparse; u=urlparse(os.environ["DATABASE_URL"]); print(u.port or 5432)')
  until nc -z "$DB_HOST" "$DB_PORT"; do sleep 1; done
fi
if [ -n "${REDIS_URL:-}" ]; then
  REDIS_HOST=$(python -c 'import os; from urllib.parse import urlparse; u=urlparse(os.environ["REDIS_URL"]); print(u.hostname or "redis")')
  REDIS_PORT=$(python -c 'import os; from urllib.parse import urlparse; u=urlparse(os.environ["REDIS_URL"]); print(u.port or 6379)')
  until nc -z "$REDIS_HOST" "$REDIS_PORT"; do sleep 1; done
fi
[ -s "static/vendor/bootstrap/bootstrap.min.css" ] || /app/scripts/fetch_frontend_assets.sh
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec "$@"
