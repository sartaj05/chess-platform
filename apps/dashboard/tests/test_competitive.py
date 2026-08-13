import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.rooms.models import Room


@pytest.mark.django_db
def test_leaderboard_orders_players_by_rating(client):
    leader = User.objects.create_user(email="leader@example.com", password="StrongPass123!", rating=1500)
    User.objects.create_user(email="second@example.com", password="StrongPass123!", rating=1400)
    response = client.get(reverse("dashboard:leaderboard"))
    assert response.status_code == 200
    assert list(response.context["players"])[0] == leader


@pytest.mark.django_db
def test_matchmaking_pairs_waiting_rated_players(client):
    first = User.objects.create_user(email="first-match@example.com", password="StrongPass123!", rating=1250)
    second = User.objects.create_user(email="second-match@example.com", password="StrongPass123!", rating=1300)
    client.force_login(first)
    first_response = client.post(reverse("rooms:matchmaking"))
    room = Room.objects.get(host=first)
    assert first_response.status_code == 302
    client.force_login(second)
    response = client.post(reverse("rooms:matchmaking"))
    assert response.status_code == 302
    assert room.participants.filter(user=second).exists()
    room.refresh_from_db()
    assert room.status == Room.Status.READY


@pytest.mark.django_db
def test_mobile_matchmaking_api_is_live(client):
    first = User.objects.create_user(email="api-first@example.com", password="StrongPass123!", rating=1200)
    second = User.objects.create_user(email="api-second@example.com", password="StrongPass123!", rating=1250)
    client.force_login(first)
    first_response = client.post(reverse("api:rooms-api:matchmaking"))
    assert first_response.status_code == 200 and first_response.json()["matched"] is False
    client.force_login(second)
    second_response = client.post(reverse("api:rooms-api:matchmaking"))
    assert second_response.status_code == 200 and second_response.json()["matched"] is True


@pytest.mark.django_db
def test_public_profile_and_history_render(client):
    player = User.objects.create_user(email="profile@example.com", password="StrongPass123!", rating=1420)
    assert client.get(reverse("accounts:public_profile", args=[player.pk])).status_code == 200
    client.force_login(player)
    assert client.get(reverse("accounts:game_history")).status_code == 200
