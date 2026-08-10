from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.core.models import TimeStampedModel


class Conversation(TimeStampedModel):
    first_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_conversations_first",
    )
    second_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_conversations_second",
    )

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["first_user", "second_user"], name="chat_unique_user_pair"),
            models.CheckConstraint(condition=~Q(first_user=F("second_user")), name="chat_prevent_self_pair"),
        ]

    def __str__(self) -> str:
        return f"{self.first_user} / {self.second_user}"

    def involves(self, user) -> bool:
        return self.first_user_id == user.pk or self.second_user_id == user.pk

    def other_user(self, user):
        return self.second_user if self.first_user_id == user.pk else self.first_user


class Message(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages_sent")
    body = models.TextField(max_length=2000)
    read_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["conversation", "created_at"], name="chat_message_created_idx")]

    def __str__(self) -> str:
        return f"{self.sender}: {self.body[:40]}"
