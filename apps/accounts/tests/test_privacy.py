import json

import pytest
from django.urls import reverse

from apps.accounts.models import User, UserPreference
from apps.games.models import Game


@pytest.fixture
def account_user(db):
    return User.objects.create_user(email="privacy@example.com", password="StrongPass123!", is_email_verified=True)


def test_user_can_update_privacy_and_notification_preferences(client, account_user):
    client.force_login(account_user)
    response = client.post(
        reverse("accounts:privacy"),
        {
            "profile_visibility": "private",
            "notify_messages": "on",
            "notify_system": "on",
        },
    )
    preferences = UserPreference.objects.get(user=account_user)
    assert response.status_code == 302
    assert preferences.profile_visibility == UserPreference.ProfileVisibility.PRIVATE
    assert preferences.allow_friend_requests is False


def test_personal_data_export_contains_account_and_games(client, account_user):
    Game.objects.create(white_user=account_user, white_display_name="Privacy", black_display_name="Bot")
    client.force_login(account_user)
    response = client.get(reverse("accounts:data_export"))
    payload = json.loads(response.content)
    assert response["Content-Disposition"].startswith("attachment;")
    assert payload["account"]["email"] == account_user.email
    assert len(payload["games"]) == 1


def test_account_deletion_requires_password_and_confirmation(client, account_user):
    client.force_login(account_user)
    failed = client.post(reverse("accounts:delete_account"), {"password": "wrong", "confirmation": "DELETE"})
    assert failed.status_code == 200
    assert User.objects.filter(pk=account_user.pk).exists()

    response = client.post(
        reverse("accounts:delete_account"),
        {"password": "StrongPass123!", "confirmation": "DELETE"},
    )
    assert response.status_code == 302
    assert not User.objects.filter(pk=account_user.pk).exists()


def test_private_profile_is_hidden_from_other_users(client, account_user):
    UserPreference.objects.create(user=account_user, profile_visibility="private")
    assert client.get(reverse("accounts:public_profile", args=[account_user.pk])).status_code == 404
    client.force_login(account_user)
    assert client.get(reverse("accounts:public_profile", args=[account_user.pk])).status_code == 200
