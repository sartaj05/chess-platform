import pytest
from apps.accounts.models import User
from apps.games.models import FairPlayAppeal, FairPlayReview, Game
from django.urls import reverse


@pytest.fixture
def fair_play_case(db):
    player = User.objects.create_user(email="player-case@example.com", password="StrongPass123!")
    opponent = User.objects.create_user(email="opponent-case@example.com")
    moderator = User.objects.create_user(email="moderator@example.com", is_staff=True)
    outsider = User.objects.create_user(email="outsider-case@example.com")
    game = Game.objects.create(
        white_user=player,
        black_user=opponent,
        white_display_name="Player",
        black_display_name="Opponent",
    )
    review = FairPlayReview.objects.create(game=game, status="flagged", risk_score=82)
    return player, moderator, outsider, review


def test_moderator_dashboard_is_staff_only(client, fair_play_case):
    player, moderator, _, review = fair_play_case
    client.force_login(player)
    assert client.get(reverse("games:moderator_dashboard")).status_code == 403
    client.force_login(moderator)
    response = client.get(reverse("games:moderator_dashboard"))
    assert response.status_code == 200
    assert str(review.risk_score).encode() in response.content


def test_player_can_appeal_and_moderator_can_overturn(client, fair_play_case):
    player, moderator, outsider, review = fair_play_case
    client.force_login(outsider)
    assert client.post(reverse("games:appeal_create", args=[review.pk]), {"statement": "No"}).status_code == 403

    client.force_login(player)
    response = client.post(
        reverse("games:appeal_create", args=[review.pk]),
        {"statement": "Please review the full move timings."},
    )
    assert response.status_code == 302
    appeal = FairPlayAppeal.objects.get(review=review, appellant=player)

    client.force_login(moderator)
    client.post(
        reverse("games:appeal_resolve", args=[appeal.pk]),
        {"status": "overturned", "response": "Timing evidence supports the appeal."},
    )
    appeal.refresh_from_db()
    review.refresh_from_db()
    assert appeal.status == FairPlayAppeal.Status.OVERTURNED
    assert review.status == FairPlayReview.Status.DISMISSED
