from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

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


@transaction.atomic
def edit_message(*, message: Message, actor: User, body: str) -> Message:
    message = Message.objects.select_for_update().get(pk=message.pk)
    if message.sender_id != actor.pk:
        raise PermissionDenied("You can only edit your own messages.")
    if message.unsent_at is not None:
        raise ValidationError("An unsent message cannot be edited.")
    if timezone.now() > message.created_at + timedelta(minutes=1):
        raise ValidationError("Messages can only be edited within 1 minute.")
    clean_body = body.strip()
    if not clean_body:
        raise ValidationError("Message cannot be empty.")
    message.body = clean_body
    message.edited_at = timezone.now()
    message.save(update_fields=["body", "edited_at", "updated_at"])
    return message


@transaction.atomic
def delete_message_for_sender(*, message: Message, actor: User) -> None:
    message = Message.objects.select_for_update().get(pk=message.pk)
    if message.sender_id != actor.pk:
        raise PermissionDenied("You can only delete your own messages.")
    if timezone.now() > message.created_at + timedelta(minutes=10):
        raise ValidationError("Messages can only be deleted within 10 minutes.")
    message.deleted_for_sender = True
    message.save(update_fields=["deleted_for_sender", "updated_at"])


@transaction.atomic
def unsend_message(*, message: Message, actor: User) -> Message:
    message = Message.objects.select_for_update().get(pk=message.pk)
    if message.sender_id != actor.pk:
        raise PermissionDenied("You can only unsend your own messages.")
    if message.unsent_at is None:
        message.body = ""
        message.unsent_at = timezone.now()
        message.save(update_fields=["body", "unsent_at", "updated_at"])
    return message
