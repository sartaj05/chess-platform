from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Friendship


@transaction.atomic
def send_friend_request(*, requester: User, email: str) -> Friendship:
    try:
        addressee = User.objects.get(email__iexact=email.strip())
    except User.DoesNotExist as exc:
        raise ValidationError("No account exists with that email address.") from exc
    if requester.pk == addressee.pk:
        raise ValidationError("You cannot send a friend request to yourself.")

    existing = Friendship.objects.filter(
        Q(requester=requester, addressee=addressee) | Q(requester=addressee, addressee=requester)
    ).first()
    if existing:
        if existing.status == Friendship.Status.ACCEPTED:
            raise ValidationError("You are already friends.")
        if existing.status == Friendship.Status.PENDING:
            raise ValidationError("A friend request is already pending.")
        existing.requester = requester
        existing.addressee = addressee
        existing.status = Friendship.Status.PENDING
        existing.save(update_fields=["requester", "addressee", "status", "updated_at"])
        friendship = existing
    else:
        friendship = Friendship.objects.create(requester=requester, addressee=addressee)
    notify(
        recipient=addressee,
        kind=Notification.Kind.FRIEND_REQUEST,
        title=f"{requester.display_name} sent you a friend request",
        target_url="/friends/",
    )
    return friendship


def respond_to_request(*, friendship: Friendship, actor: User, accept: bool) -> Friendship:
    if friendship.addressee_id != actor.pk or friendship.status != Friendship.Status.PENDING:
        raise PermissionDenied("This friend request cannot be changed.")
    friendship.status = Friendship.Status.ACCEPTED if accept else Friendship.Status.DECLINED
    friendship.save(update_fields=["status", "updated_at"])
    notify(
        recipient=friendship.requester,
        kind=Notification.Kind.FRIEND_ACCEPTED if accept else Notification.Kind.FRIEND_DECLINED,
        title=f"{actor.display_name} {'accepted' if accept else 'declined'} your friend request",
        target_url="/friends/",
    )
    return friendship


def remove_friendship(*, friendship: Friendship, actor: User) -> None:
    if not friendship.involves(actor):
        raise PermissionDenied("You cannot remove this friendship.")
    friendship.delete()
