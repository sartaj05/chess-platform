from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.games.models import Game
from apps.tournaments.models import ClubMembership, Tournament, TournamentEntry, TournamentPairing
from apps.tournaments.services import (
    create_club,
    create_simul,
    create_team_competition,
    enter_club,
    join_simul,
    start_simul,
    start_team_competition,
    start_tournament,
)


@pytest.mark.django_db
def test_starting_tournament_creates_playable_games():
    organizer = User.objects.create_user(email="auto-organizer@example.com")
    player = User.objects.create_user(email="auto-player@example.com")
    tournament = Tournament.objects.create(
        name="Automatic boards", organizer=organizer, starts_at=timezone.now() + timedelta(hours=1)
    )
    TournamentEntry.objects.create(tournament=tournament, user=organizer)
    TournamentEntry.objects.create(tournament=tournament, user=player)

    start_tournament(tournament=tournament, actor=organizer)

    pairing = TournamentPairing.objects.get(round__tournament=tournament)
    assert pairing.game is not None
    assert pairing.game.status == Game.Status.ACTIVE
    assert pairing.game.white_user == organizer
    pairing.game.finish(
        result=Game.Result.WHITE_WIN,
        termination=Game.Termination.RESIGNATION,
        winner_color=Game.Color.WHITE,
    )
    pairing.refresh_from_db()
    assert pairing.result == TournamentPairing.Result.WHITE_WIN


@pytest.mark.django_db
def test_club_team_event_and_simul_create_live_boards():
    organizer = User.objects.create_user(email="club-organizer@example.com")
    opponent = User.objects.create_user(email="club-opponent@example.com")
    home = create_club(owner=organizer, name="Home Knights", slug="home-knights")
    away = create_club(owner=opponent, name="Away Bishops", slug="away-bishops")
    ClubMembership.objects.filter(club=away, user=opponent).update(role=ClubMembership.Role.CAPTAIN)
    competition = create_team_competition(
        organizer=organizer, name="Club League", starts_at=timezone.now() + timedelta(hours=2), boards_per_team=1
    )
    enter_club(competition=competition, club=home, captain=organizer)
    enter_club(competition=competition, club=away, captain=opponent)
    start_team_competition(competition=competition, actor=organizer)
    assert competition.boards.count() == 1
    assert competition.boards.get().game.status == Game.Status.ACTIVE

    simul = create_simul(host=organizer, name="Coach Simul", starts_at=timezone.now(), max_opponents=4)
    join_simul(exhibition=simul, opponent=opponent)
    start_simul(exhibition=simul, actor=organizer)
    assert simul.seats.get().game.status == Game.Status.ACTIVE
