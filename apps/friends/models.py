from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.core.models import TimeStampedModel


class Friendship(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_sent",
    )
    addressee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_received",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["requester", "addressee"], name="friends_unique_direction"),
            models.CheckConstraint(condition=~Q(requester=F("addressee")), name="friends_prevent_self"),
        ]
        indexes = [
            models.Index(fields=["requester", "status"], name="friends_request_status_idx"),
            models.Index(fields=["addressee", "status"], name="friends_address_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.requester} -> {self.addressee} ({self.status})"

    def involves(self, user) -> bool:
        return self.requester_id == user.pk or self.addressee_id == user.pk

    def other_user(self, user):
        return self.addressee if self.requester_id == user.pk else self.requester


class UserBlock(TimeStampedModel):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_created")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_received")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["blocker", "blocked"], name="friends_unique_block")]


class UserReport(TimeStampedModel):
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_created")
    reported = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_received")
    reason = models.CharField(max_length=32, default="other")
    details = models.TextField(max_length=1000, blank=True)
    status = models.CharField(max_length=16, default="open", db_index=True)


class FriendChallenge(TimeStampedModel):
    challenger = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="challenges_sent")
    challenged = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="challenges_received"
    )
    room = models.ForeignKey(
        "rooms.Room", on_delete=models.SET_NULL, null=True, blank=True, related_name="friend_challenges"
    )
    status = models.CharField(max_length=16, default="pending", db_index=True)

    class Meta:
        ordering = ["-created_at"]
