from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q

from apps.accounts.models import User
from apps.friends.models import Friendship, UserBlock
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Conversation, Message


def users_are_friends(first: User, second: User) -> bool:
    return not UserBlock.objects.filter(Q(blocker=first, blocked=second) | Q(blocker=second, blocked=first)).exists() and Friendship.objects.filter(
        Q(requester=first, addressee=second) | Q(requester=second, addressee=first),
        status=Friendship.Status.ACCEPTED,
    ).exists()


@transaction.atomic
def get_or_create_conversation(*, actor: User, other: User) -> Conversation:
    if actor.pk == other.pk:
        raise ValidationError("You cannot start a conversation with yourself.")
    if not users_are_friends(actor, other):
        raise PermissionDenied("You can only message accepted friends.")
    first, second = sorted((actor, other), key=lambda user: str(user.pk))
    conversation, _ = Conversation.objects.get_or_create(first_user=first, second_user=second)
    return conversation


@transaction.atomic
def send_message(*, conversation: Conversation, sender: User, body: str) -> Message:
    if not conversation.involves(sender):
        raise PermissionDenied("You are not part of this conversation.")
    recipient = conversation.other_user(sender)
    if not users_are_friends(sender, recipient):
        raise PermissionDenied("You can only message accepted friends.")
    clean_body = body.strip()
    if not clean_body:
        raise ValidationError("Message cannot be empty.")
    message = Message.objects.create(conversation=conversation, sender=sender, body=clean_body)
    conversation.save(update_fields=["updated_at"])
    notify(
        recipient=recipient,
        kind=Notification.Kind.DIRECT_MESSAGE,
        title=f"New message from {sender.display_name}",
        message=clean_body[:255],
        target_url=f"/chat/{conversation.pk}/",
    )
    return message
