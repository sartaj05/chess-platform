from __future__ import annotations

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
    return Notification.objects.create(
        recipient=recipient,
        kind=kind,
        title=title,
        message=message,
        target_url=target_url,
    )
