from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.notifications.models import Notification


@pytest.fixture
def notification_users(db):
    first = User.objects.create_user(email="notify@example.com", password="test-pass-123")
    second = User.objects.create_user(email="other@example.com", password="test-pass-123")
    return first, second


def test_notification_list_requires_login(client):
    assert client.get(reverse("notifications:list")).status_code == 302


def test_user_only_sees_own_notifications(client, notification_users):
    first, second = notification_users
    Notification.objects.create(recipient=first, title="Visible")
    Notification.objects.create(recipient=second, title="Hidden")
    client.force_login(first)
    response = client.get(reverse("notifications:list"))
    assert response.status_code == 200
    assert b"Visible" in response.content
    assert b"Hidden" not in response.content


def test_mark_notification_read_and_follow_internal_target(client, notification_users):
    first, _ = notification_users
    notification = Notification.objects.create(recipient=first, title="Friend update", target_url="/friends/")
    client.force_login(first)
    response = client.post(reverse("notifications:read", args=[notification.pk]))
    assert response.status_code == 302
    assert response.url == "/friends/"
    notification.refresh_from_db()
    assert notification.is_read


def test_user_cannot_read_another_users_notification(client, notification_users):
    first, second = notification_users
    notification = Notification.objects.create(recipient=second, title="Private")
    client.force_login(first)
    response = client.post(reverse("notifications:read", args=[notification.pk]))
    assert response.status_code == 404
    notification.refresh_from_db()
    assert not notification.is_read


def test_mark_all_only_updates_current_user(client, notification_users):
    first, second = notification_users
    own = Notification.objects.create(recipient=first, title="Own")
    other = Notification.objects.create(recipient=second, title="Other")
    client.force_login(first)
    response = client.post(reverse("notifications:read_all"))
    assert response.status_code == 302
    own.refresh_from_db()
    other.refresh_from_db()
    assert own.is_read
    assert not other.is_read
