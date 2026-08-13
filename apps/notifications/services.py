from __future__ import annotations

from django.db import transaction
from apps.accounts.models import User

from .models import Notification


def notify(
    *,
    recipient: User,
    kind: str,
    title: str,
    message: str = "",
    target_url: str = "",
) -> Notification:
    notification = Notification.objects.create(
        recipient=recipient,
        kind=kind,
        title=title,
        message=message,
        target_url=target_url,
    )
    transaction.on_commit(lambda: _queue_push(notification.pk))
    return notification


def _queue_push(notification_id: int) -> None:
    from .tasks import send_push_notification
    send_push_notification.delay(notification_id)
