from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.friends.models import Friendship
from apps.notifications.models import Notification
from apps.chat.models import Conversation, Message


@pytest.fixture
def users(db):
    first = User.objects.create_user(email="first@example.com", password="test-pass-123")
    second = User.objects.create_user(email="second@example.com", password="test-pass-123")
    outsider = User.objects.create_user(email="outsider@example.com", password="test-pass-123")
    return first, second, outsider


def test_friends_page_requires_login(client):
    response = client.get(reverse("friends:list"))
    assert response.status_code == 302


def test_send_and_accept_friend_request(client, users):
    first, second, _ = users
    client.force_login(first)
    response = client.post(reverse("friends:send"), {"email": second.email})
    assert response.status_code == 302
    friendship = Friendship.objects.get(requester=first, addressee=second)
    assert friendship.status == Friendship.Status.PENDING
    assert Notification.objects.filter(recipient=second, kind=Notification.Kind.FRIEND_REQUEST).exists()

    client.force_login(second)
    response = client.post(reverse("friends:accept", args=[friendship.pk]))
    assert response.status_code == 302
    friendship.refresh_from_db()
    assert friendship.status == Friendship.Status.ACCEPTED
    assert Notification.objects.filter(recipient=first, kind=Notification.Kind.FRIEND_ACCEPTED).exists()


def test_cannot_friend_self_or_duplicate(client, users):
    first, second, _ = users
    client.force_login(first)
    client.post(reverse("friends:send"), {"email": first.email})
    assert not Friendship.objects.exists()

    client.post(reverse("friends:send"), {"email": second.email})
    client.post(reverse("friends:send"), {"email": second.email})
    assert Friendship.objects.count() == 1


def test_outsider_cannot_accept_or_remove(client, users):
    first, second, outsider = users
    friendship = Friendship.objects.create(requester=first, addressee=second)
    client.force_login(outsider)
    client.post(reverse("friends:accept", args=[friendship.pk]))
    friendship.refresh_from_db()
    assert friendship.status == Friendship.Status.PENDING

    client.post(reverse("friends:remove", args=[friendship.pk]))
    assert Friendship.objects.filter(pk=friendship.pk).exists()


def test_friend_can_remove_relationship(client, users):
    first, second, _ = users
    friendship = Friendship.objects.create(
        requester=first,
        addressee=second,
        status=Friendship.Status.ACCEPTED,
    )
    client.force_login(second)
    client.post(reverse("friends:remove", args=[friendship.pk]))
    assert not Friendship.objects.filter(pk=friendship.pk).exists()


def test_mobile_social_api_exposes_and_applies_message_controls(client, users):
    first, second, _ = users
    Friendship.objects.create(requester=first, addressee=second, status=Friendship.Status.ACCEPTED)
    conversation = Conversation.objects.create(first_user=first, second_user=second)
    message = Message.objects.create(conversation=conversation, sender=first, body="Mobile original")
    client.force_login(first)

    response = client.get("/api/social/")
    mobile_message = response.json()["conversations"][0]["messages"][0]
    assert mobile_message["can_edit"] is True
    assert mobile_message["can_delete"] is True
    assert mobile_message["can_unsend"] is True

    response = client.post(
        "/api/social/",
        {"action": "edit_message", "conversation_id": conversation.pk, "message_id": message.pk, "body": "Mobile edited"},
        content_type="application/json",
    )
    assert response.status_code == 200
    message.refresh_from_db()
    assert message.body == "Mobile edited"

    response = client.post(
        "/api/social/",
        {"action": "unsend_message", "conversation_id": conversation.pk, "message_id": message.pk},
        content_type="application/json",
    )
    assert response.status_code == 200
    message.refresh_from_db()
    assert message.unsent_at is not None
