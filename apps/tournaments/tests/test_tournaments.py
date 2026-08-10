from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.tournaments.models import Tournament, TournamentEntry


@pytest.fixture
def tournament_users(db):
    organizer = User.objects.create_user(email="organizer@example.com", password="test-pass-123")
    player = User.objects.create_user(email="player@example.com", password="test-pass-123")
    outsider = User.objects.create_user(email="outsider@example.com", password="test-pass-123")
    return organizer, player, outsider


@pytest.fixture
def tournament(tournament_users):
    organizer, _, _ = tournament_users
    return Tournament.objects.create(
        name="Weekend Swiss",
        organizer=organizer,
        starts_at=timezone.now() + timedelta(days=1),
        max_players=2,
    )


def test_public_can_browse_tournaments(client, tournament):
    response = client.get(reverse("tournaments:list"))
    assert response.status_code == 200
    assert b"Weekend Swiss" in response.content


def test_authenticated_user_can_create_tournament(client, tournament_users):
    organizer, _, _ = tournament_users
    client.force_login(organizer)
    response = client.post(
        reverse("tournaments:create"),
        {
            "name": "Rapid Cup",
            "description": "Friendly rapid event",
            "format": Tournament.Format.SWISS,
            "starts_at": (timezone.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            "max_players": 8,
            "clock_initial_minutes": 10,
            "increment_seconds": 5,
            "is_public": "on",
        },
    )
    created = Tournament.objects.get(name="Rapid Cup")
    assert response.status_code == 302
    assert created.organizer == organizer
    assert TournamentEntry.objects.filter(tournament=created, user=organizer).exists()


def test_join_enforces_capacity_and_creates_notification(client, tournament_users, tournament):
    organizer, player, outsider = tournament_users
    TournamentEntry.objects.create(tournament=tournament, user=organizer)
    client.force_login(player)
    client.post(reverse("tournaments:join", args=[tournament.pk]))
    assert TournamentEntry.objects.filter(tournament=tournament, user=player).exists()
    assert Notification.objects.filter(recipient=organizer, kind=Notification.Kind.TOURNAMENT).exists()

    client.force_login(outsider)
    client.post(reverse("tournaments:join", args=[tournament.pk]))
    assert not TournamentEntry.objects.filter(tournament=tournament, user=outsider).exists()


def test_only_organizer_can_start_tournament(client, tournament_users, tournament):
    organizer, player, outsider = tournament_users
    TournamentEntry.objects.create(tournament=tournament, user=organizer)
    TournamentEntry.objects.create(tournament=tournament, user=player)
    client.force_login(outsider)
    client.post(reverse("tournaments:start", args=[tournament.pk]))
    tournament.refresh_from_db()
    assert tournament.status == Tournament.Status.REGISTRATION

    client.force_login(organizer)
    client.post(reverse("tournaments:start", args=[tournament.pk]))
    tournament.refresh_from_db()
    assert tournament.status == Tournament.Status.ACTIVE
    assert list(tournament.entries.order_by("seed").values_list("seed", flat=True)) == [1, 2]
    assert Notification.objects.filter(kind=Notification.Kind.TOURNAMENT, title__contains="has started").count() == 2


def test_cannot_withdraw_after_start(client, tournament_users, tournament):
    organizer, player, _ = tournament_users
    TournamentEntry.objects.create(tournament=tournament, user=organizer)
    TournamentEntry.objects.create(tournament=tournament, user=player)
    tournament.status = Tournament.Status.ACTIVE
    tournament.save(update_fields=["status"])
    client.force_login(player)
    client.post(reverse("tournaments:withdraw", args=[tournament.pk]))
    assert TournamentEntry.objects.filter(tournament=tournament, user=player).exists()


def test_private_tournament_hidden_from_non_organizer(client, tournament_users, tournament):
    organizer, player, _ = tournament_users
    tournament.is_public = False
    tournament.save(update_fields=["is_public"])
    assert client.get(tournament.get_absolute_url()).status_code == 404
    client.force_login(player)
    assert client.get(tournament.get_absolute_url()).status_code == 404
    client.force_login(organizer)
    assert client.get(tournament.get_absolute_url()).status_code == 200
