from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    class Kind(models.TextChoices):
        FRIEND_REQUEST = "friend_request", "Friend request"
        FRIEND_ACCEPTED = "friend_accepted", "Friend accepted"
        FRIEND_DECLINED = "friend_declined", "Friend declined"
        DIRECT_MESSAGE = "direct_message", "Direct message"
        TOURNAMENT = "tournament", "Tournament"
        SYSTEM = "system", "System"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices, default=Kind.SYSTEM, db_index=True)
    title = models.CharField(max_length=120)
    message = models.CharField(max_length=255, blank=True)
    target_url = models.CharField(max_length=255, blank=True)
    read_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "read_at", "created_at"], name="notify_user_read_created_idx")]

    def __str__(self) -> str:
        return f"{self.recipient}: {self.title}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self) -> None:
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at", "updated_at"])


class PushDevice(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_devices")
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=12, default="android")
    active = models.BooleanField(default=True, db_index=True)
    last_seen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["user", "active"], name="push_device_user_active_idx")]
