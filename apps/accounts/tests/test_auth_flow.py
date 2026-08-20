from unittest.mock import patch

import pytest
from django.urls import reverse
from kombu.exceptions import OperationalError

from apps.accounts.models import EmailOTP, User


@pytest.mark.django_db
def test_create_user_with_email():
    user = User.objects.create_user(email="PLAYER@example.com", password="StrongPass123!")
    assert user.email == "player@example.com"
    assert user.check_password("StrongPass123!")


def test_login_page_displays_email_password_form(client):
    response = client.get(reverse("accounts:login"))

    assert response.status_code == 200
    assert b'name="email"' in response.content
    assert b'name="password"' in response.content
    assert b"Sign in via" not in response.content


@pytest.mark.django_db
def test_verified_user_can_login_from_email_form(client):
    User.objects.create_user(
        email="verified@example.com",
        password="StrongPass123!",
        is_email_verified=True,
    )

    response = client.post(
        reverse("accounts:login"),
        {"email": "verified@example.com", "password": "StrongPass123!"},
    )

    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
@patch("apps.accounts.views.send_email_verification.apply")
@patch(
    "apps.accounts.views.send_email_verification.delay",
    side_effect=OperationalError("broker unavailable"),
)
def test_unverified_login_survives_celery_broker_outage(delay, apply, client):
    user = User.objects.create_user(
        email="pending@example.com",
        password="StrongPass123!",
        is_active=False,
        is_email_verified=False,
    )

    response = client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "StrongPass123!"},
    )

    assert response.status_code == 302
    assert response.url == reverse("accounts:verify_email")
    delay.assert_called_once()
    apply.assert_called_once()


@pytest.mark.django_db
def test_signup_creates_inactive_user_and_otp(client):
    response = client.post(
        reverse("accounts:signup"),
        {
            "email": "newplayer@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
            "accept_terms": "on",
        },
    )
    assert response.status_code == 302
    user = User.objects.get(email="newplayer@example.com")
    assert user.is_active is False
    assert EmailOTP.objects.filter(user=user, purpose=EmailOTP.Purpose.VERIFY_EMAIL).exists()


@pytest.mark.django_db
def test_me_api_requires_authentication(client):
    response = client.get(reverse("api:accounts_api:me"))
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_mobile_registration_and_email_verification(client, monkeypatch):
    sent = {}

    def fake_send(user_id, request_host, scheme, ip_address=None, user_agent=""):
        user = User.objects.get(id=user_id)
        _, sent["code"] = EmailOTP.create_code(user=user, purpose=EmailOTP.Purpose.VERIFY_EMAIL)

    monkeypatch.setattr("apps.accounts.api_views.send_email_verification", fake_send)
    response = client.post(
        reverse("api:accounts_api:register"),
        {"email": "mobile@example.com", "display_name": "Mobile", "password": "StrongPass123!"},
        content_type="application/json",
    )
    assert response.status_code == 201
    user = User.objects.get(email="mobile@example.com")
    assert user.is_active is False

    response = client.post(
        reverse("api:accounts_api:verify-email"),
        {"email": user.email, "code": sent["code"]},
        content_type="application/json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_active is True
    assert user.is_email_verified is True


@pytest.mark.django_db
def test_mobile_bot_victory_advances_current_level(client):
    user = User.objects.create_user(email="mobile-bot@example.com", password="StrongPass123!")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
    response = client.post(
        reverse("api:accounts_api:bot-victory"),
        {"level": 1},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.data["bot_level"] == 2


@pytest.mark.django_db
def test_mobile_experience_returns_recommendations_and_achievements(client):
    user = User.objects.create_user(email="experience@example.com", password="StrongPass123!")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    response = client.get(reverse("api:accounts_api:experience"))

    assert response.status_code == 200
    assert response.data["recommendations"][0]["kind"] == "TRAINING"
    assert response.data["achievements"][0]["name"] == "First Move"
    assert len(response.data["daily_goals"]) == 3
    assert response.data["live_activity"] == {
        "active_game_count": 0,
        "active_player_count": 0,
        "active_games": [],
        "resume_games": [],
        "recent_winners": [],
    }
    assert response.data["live_activity"] == {
        "active_game_count": 0,
        "active_player_count": 0,
        "active_games": [],
        "resume_games": [],
        "recent_winners": [],
    }


@pytest.mark.django_db
def test_mobile_player_comparison_returns_both_players(client):
    user = User.objects.create_user(email="first@example.com", password="StrongPass123!")
    other = User.objects.create_user(email="second@example.com", password="StrongPass123!")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    response = client.get(
        reverse("api:accounts_api:player-comparison", kwargs={"pk": other.pk})
    )

    assert response.status_code == 200
    assert response.data["first"]["profile"]["email"] == user.email
    assert response.data["second"]["profile"]["email"] == other.email
    assert response.data["first"]["win_rate"] == 0
