FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev netcat-openbsd gettext curl ca-certificates stockfish && rm -rf /var/lib/apt/lists/*
COPY requirements /app/requirements
RUN pip install --upgrade pip && pip install -r requirements/prod.txt
COPY . /app
RUN chmod +x /app/entrypoint.sh /app/scripts/fetch_frontend_assets.sh && /app/scripts/fetch_frontend_assets.sh
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "chess_platform.asgi:application", "-c", "gunicorn.conf.py"]
