from __future__ import annotations
import os
from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_platform.settings.dev")
app = Celery("chess_platform")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {"cleanup-expired-email-otps-every-hour": {"task": "accounts.cleanup_expired_otps", "schedule": 3600.0}}
