from __future__ import annotations

from django.db import transaction

from apps.accounts.models import User, UserPreference

from .models import Notification


def notify(
    *,
    recipient: User,
    kind: str,
    title: str,
    message: str = "",
    target_url: str = "",
) -> Notification | None:
    preferences, _ = UserPreference.objects.get_or_create(user=recipient)
    enabled = {
        Notification.Kind.FRIEND_REQUEST: preferences.notify_friend_activity,
        Notification.Kind.FRIEND_ACCEPTED: preferences.notify_friend_activity,
        Notification.Kind.FRIEND_DECLINED: preferences.notify_friend_activity,
        Notification.Kind.DIRECT_MESSAGE: preferences.notify_messages,
        Notification.Kind.TOURNAMENT: preferences.notify_tournaments,
        Notification.Kind.SYSTEM: preferences.notify_system,
    }.get(kind, True)
    if not enabled:
        return None
    notification = Notification.objects.create(
        recipient=recipient,
        kind=kind,
        title=title,
        message=message,
        target_url=target_url,
    )
    if preferences.push_enabled:
        transaction.on_commit(lambda: _queue_push(notification.pk))
    return notification


def _queue_push(notification_id: int) -> None:
    from .tasks import send_push_notification

    send_push_notification.delay(notification_id)
