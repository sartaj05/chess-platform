from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.chat.models import Conversation, Message
from apps.friends.models import Friendship
from apps.notifications.models import Notification


@pytest.fixture
def chat_users(db):
    first = User.objects.create_user(email="chat-one@example.com", password="test-pass-123")
    second = User.objects.create_user(email="chat-two@example.com", password="test-pass-123")
    outsider = User.objects.create_user(email="chat-out@example.com", password="test-pass-123")
    Friendship.objects.create(requester=first, addressee=second, status=Friendship.Status.ACCEPTED)
    return first, second, outsider


def test_chat_requires_login(client):
    assert client.get(reverse("chat:list")).status_code == 302


def test_friends_can_start_conversation_and_send_message(client, chat_users):
    first, second, _ = chat_users
    client.force_login(first)
    response = client.post(reverse("chat:start", args=[second.pk]))
    conversation = Conversation.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("chat:thread", args=[conversation.pk])

    response = client.post(reverse("chat:thread", args=[conversation.pk]), {"body": "Ready for a game?"})
    assert response.status_code == 302
    assert Message.objects.filter(conversation=conversation, sender=first, body="Ready for a game?").exists()
    assert Notification.objects.filter(recipient=second, kind=Notification.Kind.DIRECT_MESSAGE).exists()


def test_non_friends_cannot_start_conversation(client, chat_users):
    first, _, outsider = chat_users
    client.force_login(first)
    response = client.post(reverse("chat:start", args=[outsider.pk]))
    assert response.status_code == 302
    assert response.url == reverse("friends:list")
    assert not Conversation.objects.exists()


def test_outsider_cannot_view_or_post_to_thread(client, chat_users):
    first, second, outsider = chat_users
    conversation = Conversation.objects.create(first_user=first, second_user=second)
    client.force_login(outsider)
    assert client.get(reverse("chat:thread", args=[conversation.pk])).status_code == 404
    assert client.post(reverse("chat:thread", args=[conversation.pk]), {"body": "Intrusion"}).status_code == 404
    assert not Message.objects.exists()


def test_opening_thread_marks_only_received_messages_read(client, chat_users):
    first, second, _ = chat_users
    conversation = Conversation.objects.create(first_user=first, second_user=second)
    received = Message.objects.create(conversation=conversation, sender=second, body="Hello")
    sent = Message.objects.create(conversation=conversation, sender=first, body="Hi")
    client.force_login(first)
    response = client.get(reverse("chat:thread", args=[conversation.pk]))
    assert b"message-bubble" in response.content
    assert b"Back to messages" not in response.content
    assert response.status_code == 200
    received.refresh_from_db()
    sent.refresh_from_db()
    assert received.read_at is not None
    assert sent.read_at is None


def test_removed_friends_cannot_send_more_messages(client, chat_users):
    first, second, _ = chat_users
    conversation = Conversation.objects.create(first_user=first, second_user=second)
    Friendship.objects.all().delete()
    client.force_login(first)
    client.post(reverse("chat:thread", args=[conversation.pk]), {"body": "Blocked"})
    assert not Message.objects.exists()


def test_sender_can_edit_message_only_within_one_minute(client, chat_users):
    first, second, _ = chat_users
    conversation = Conversation.objects.create(first_user=first, second_user=second)
    message = Message.objects.create(conversation=conversation, sender=first, body="Original")
    client.force_login(first)

    client.post(reverse("chat:edit_message", args=[conversation.pk, message.pk]), {"body": "Updated"})
    message.refresh_from_db()
    assert message.body == "Updated"
    assert message.edited_at is not None

    Message.objects.filter(pk=message.pk).update(created_at=timezone.now() - timedelta(minutes=2))
    client.post(reverse("chat:edit_message", args=[conversation.pk, message.pk]), {"body": "Too late"})
    message.refresh_from_db()
    assert message.body == "Updated"


def test_sender_can_delete_for_self_only_within_ten_minutes(client, chat_users):
    first, second, _ = chat_users
    conversation = Conversation.objects.create(first_user=first, second_user=second)
    visible = Message.objects.create(conversation=conversation, sender=first, body="Hide for sender")
    expired = Message.objects.create(conversation=conversation, sender=first, body="Too old")
    Message.objects.filter(pk=expired.pk).update(created_at=timezone.now() - timedelta(minutes=11))
    client.force_login(first)

    client.post(reverse("chat:delete_message", args=[conversation.pk, visible.pk]))
    client.post(reverse("chat:delete_message", args=[conversation.pk, expired.pk]))
    visible.refresh_from_db()
    expired.refresh_from_db()
    assert visible.deleted_for_sender is True
    assert expired.deleted_for_sender is False
    assert b"Hide for sender" not in client.get(reverse("chat:thread", args=[conversation.pk])).content

    client.force_login(second)
    assert b"Hide for sender" in client.get(reverse("chat:thread", args=[conversation.pk])).content


def test_sender_can_unsend_any_time_but_recipient_cannot(client, chat_users):
    first, second, _ = chat_users
    conversation = Conversation.objects.create(first_user=first, second_user=second)
    message = Message.objects.create(conversation=conversation, sender=first, body="Old secret")
    Message.objects.filter(pk=message.pk).update(created_at=timezone.now() - timedelta(days=30))

    client.force_login(second)
    client.post(reverse("chat:unsend_message", args=[conversation.pk, message.pk]))
    message.refresh_from_db()
    assert message.unsent_at is None

    client.force_login(first)
    client.post(reverse("chat:unsend_message", args=[conversation.pk, message.pk]))
    message.refresh_from_db()
    assert message.unsent_at is not None
    assert message.body == ""
    response = client.get(reverse("chat:thread", args=[conversation.pk]))
    assert b"Message unsent" in response.content
    assert b"Old secret" not in response.content
