from __future__ import annotations

from django.db import models
from django.utils import timezone


class RoomQuerySet(models.QuerySet):
    """Reusable filters for chess rooms."""

    def active(self) -> "RoomQuerySet":
        return self.exclude(status__in=[self.model.Status.FINISHED, self.model.Status.ABORTED, self.model.Status.EXPIRED])

    def waiting(self) -> "RoomQuerySet":
        return self.filter(status=self.model.Status.WAITING)

    def public(self) -> "RoomQuerySet":
        return self.filter(visibility=self.model.Visibility.PUBLIC)

    def recently_active(self) -> "RoomQuerySet":
        return self.order_by("-last_activity_at", "-created_at")


class RoomManager(models.Manager.from_queryset(RoomQuerySet)):
    """Manager with production-friendly room creation defaults."""

    def create_room(self, **kwargs):
        kwargs.setdefault("last_activity_at", timezone.now())
        return self.create(**kwargs)
