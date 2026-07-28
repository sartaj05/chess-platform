from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.rooms.models import Room
from celery import shared_task


@shared_task
def expire_stale_waiting_rooms(hours: int = 24) -> int:
    """Expire empty or inactive waiting rooms to keep the lobby clean."""

    cutoff = timezone.now() - timedelta(hours=hours)
    queryset = Room.objects.filter(status=Room.Status.WAITING, last_activity_at__lt=cutoff)
    updated = queryset.update(status=Room.Status.EXPIRED, updated_at=timezone.now())
    return int(updated)
