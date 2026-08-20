from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserPreference
from apps.games.models import Game
from apps.tournaments.models import Tournament


@pytest.mark.django_db
def test_global_search_finds_public_entities_and_hides_private_players(client):
    visible = User.objects.create_user(email="visible@example.com", display_name="Knight Finder")
    private = User.objects.create_user(email="private@example.com", display_name="Knight Hidden")
    UserPreference.objects.create(user=private, profile_visibility="private")
    Tournament.objects.create(
        name="Knight Championship",
        organizer=visible,
        starts_at=timezone.now() + timedelta(days=1),
    )
    Game.objects.create(white_display_name="Knight Finder", black_display_name="Bot")

    response = client.get(reverse("core:search"), {"q": "Knight"})
    assert response.status_code == 200
    assert b"Knight Finder" in response.content
    assert b"Knight Hidden" not in response.content
    assert b"Knight Championship" in response.content
    assert b"Knight Finder vs Bot" in response.content
