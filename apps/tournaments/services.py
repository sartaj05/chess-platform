from __future__ import annotations

import math
import secrets
import string
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.games.models import Game
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import (
    Club,
    ClubMembership,
    SimulSeat,
    SimultaneousExhibition,
    TeamBoard,
    TeamCompetition,
    TeamCompetitionEntry,
    Tournament,
    TournamentAnnouncement,
    TournamentEntry,
    TournamentMessage,
    TournamentPairing,
    TournamentRound,
)


def invite_code(length: int = 10) -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))


def _create_pairing_game(pairing: TournamentPairing) -> Game | None:
    if pairing.black_entry_id is None:
        return None
    tournament = pairing.round.tournament
    initial_ms = tournament.clock_initial_minutes * 60 * 1000
    game = Game.objects.create(
        status=Game.Status.ACTIVE,
        rated=False,
        white_user=pairing.white_entry.user,
        black_user=pairing.black_entry.user,
        white_display_name=pairing.white_entry.user.display_name,
        black_display_name=pairing.black_entry.user.display_name,
        clock_initial_ms=initial_ms,
        increment_ms=tournament.increment_seconds * 1000,
        white_time_ms=initial_ms,
        black_time_ms=initial_ms,
        started_at=timezone.now(),
        last_move_at=timezone.now(),
        clock_started_at=timezone.now(),
        metadata={"mode": "tournament", "tournament_id": tournament.pk, "pairing_id": pairing.pk},
    )
    pairing.game = game
    pairing.save(update_fields=["game", "updated_at"])
    return game


def _maximum_rounds(tournament: Tournament, player_count: int) -> int:
    if tournament.format == Tournament.Format.ROUND_ROBIN:
        return max(1, player_count - 1 + (player_count % 2))
    return max(1, math.ceil(math.log2(max(player_count, 2))))


def _create_next_round(tournament: Tournament, number: int) -> TournamentRound:
    entries = list(tournament.entries.order_by("-score", "-buchholz", "seed"))
    previous = {
        frozenset((w, b))
        for w, b in TournamentPairing.objects.filter(
            round__tournament=tournament, black_entry__isnull=False
        ).values_list("white_entry_id", "black_entry_id")
    }
    tournament_round = TournamentRound.objects.create(tournament=tournament, number=number)
    board = 1
    while entries:
        white = entries.pop(0)
        opponent_index = (
            next((i for i, candidate in enumerate(entries) if frozenset((white.pk, candidate.pk)) not in previous), 0)
            if entries
            else None
        )
        black = entries.pop(opponent_index) if opponent_index is not None else None
        pairing = TournamentPairing.objects.create(
            round=tournament_round,
            board_number=board,
            white_entry=white,
            black_entry=black,
            result=TournamentPairing.Result.PENDING if black else TournamentPairing.Result.BYE,
        )
        if pairing.result == TournamentPairing.Result.BYE:
            white.score += 1
            white.save(update_fields=["score", "updated_at"])
        else:
            _create_pairing_game(pairing)
        board += 1
    return tournament_round


@transaction.atomic
def create_club(*, owner: User, name: str, slug: str, description: str = "") -> Club:
    club = Club.objects.create(
        owner=owner, name=name.strip()[:120], slug=slug.strip().lower(), description=description.strip()[:500],
        invite_code=invite_code(),
    )
    ClubMembership.objects.create(club=club, user=owner, role=ClubMembership.Role.OWNER)
    return club


@transaction.atomic
def join_club(*, user: User, code: str) -> ClubMembership:
    club = Club.objects.select_for_update().get(invite_code=code.strip().upper())
    membership, _ = ClubMembership.objects.get_or_create(club=club, user=user)
    return membership


@transaction.atomic
def create_team_competition(*, organizer: User, name: str, starts_at, boards_per_team: int = 4) -> TeamCompetition:
    return TeamCompetition.objects.create(
        organizer=organizer, name=name.strip()[:140], starts_at=starts_at,
        boards_per_team=max(1, min(int(boards_per_team), 20)),
    )


@transaction.atomic
def enter_club(*, competition: TeamCompetition, club: Club, captain: User) -> TeamCompetitionEntry:
    if not club.memberships.filter(user=captain, role__in=[ClubMembership.Role.OWNER, ClubMembership.Role.CAPTAIN]).exists():
        raise PermissionDenied("Only a club owner or captain can enter the club.")
    return TeamCompetitionEntry.objects.create(competition=competition, club=club, captain=captain)


@transaction.atomic
def start_team_competition(*, competition: TeamCompetition, actor: User) -> TeamCompetition:
    competition = TeamCompetition.objects.select_for_update().get(pk=competition.pk)
    if competition.organizer_id != actor.pk:
        raise PermissionDenied("Only the organizer can start this competition.")
    entries = list(competition.entries.select_related("club"))
    if len(entries) < 2:
        raise ValidationError("At least two clubs are required.")
    initial_ms = 10 * 60 * 1000
    for match_index in range(0, len(entries) - 1, 2):
        home, away = entries[match_index], entries[match_index + 1]
        home_players = list(home.club.members.order_by("club_memberships__created_at")[:competition.boards_per_team])
        away_players = list(away.club.members.order_by("club_memberships__created_at")[:competition.boards_per_team])
        board_count = min(len(home_players), len(away_players), competition.boards_per_team)
        if board_count == 0:
            continue
        for index in range(board_count):
            white, black = (home_players[index], away_players[index]) if index % 2 == 0 else (away_players[index], home_players[index])
            game = Game.objects.create(
                status=Game.Status.ACTIVE, white_user=white, black_user=black,
                white_display_name=white.display_name, black_display_name=black.display_name,
                clock_initial_ms=initial_ms, white_time_ms=initial_ms, black_time_ms=initial_ms,
                started_at=timezone.now(), last_move_at=timezone.now(), clock_started_at=timezone.now(),
                metadata={"mode": "team_competition", "competition_id": competition.pk,
                          "home_club": home.club.name, "away_club": away.club.name},
            )
            TeamBoard.objects.create(
                competition=competition, round_number=1, board_number=index + 1,
                home_club=home.club, away_club=away.club, white_player=white, black_player=black, game=game,
            )
    if not competition.boards.exists():
        raise ValidationError("The entered clubs need active members before the event can start.")
    competition.status = TeamCompetition.Status.ACTIVE
    competition.save(update_fields=["status", "updated_at"])
    return competition


@transaction.atomic
def create_simul(*, host: User, name: str, starts_at, max_opponents: int = 20, host_color: str = "white") -> SimultaneousExhibition:
    return SimultaneousExhibition.objects.create(
        host=host, name=name.strip()[:140], starts_at=starts_at,
        max_opponents=max(1, min(int(max_opponents), 100)), host_color=host_color,
        invite_code=invite_code(),
    )


@transaction.atomic
def join_simul(*, exhibition: SimultaneousExhibition, opponent: User) -> SimulSeat:
    exhibition = SimultaneousExhibition.objects.select_for_update().get(pk=exhibition.pk)
    if exhibition.status != SimultaneousExhibition.Status.REGISTRATION:
        raise ValidationError("This exhibition is no longer accepting players.")
    if exhibition.host_id == opponent.pk:
        raise ValidationError("The host cannot take an opponent seat.")
    if exhibition.seats.count() >= exhibition.max_opponents:
        raise ValidationError("This exhibition is full.")
    return SimulSeat.objects.create(exhibition=exhibition, opponent=opponent, board_number=exhibition.seats.count() + 1)


@transaction.atomic
def start_simul(*, exhibition: SimultaneousExhibition, actor: User) -> SimultaneousExhibition:
    exhibition = SimultaneousExhibition.objects.select_for_update().get(pk=exhibition.pk)
    if exhibition.host_id != actor.pk:
        raise PermissionDenied("Only the host can start this exhibition.")
    if not exhibition.seats.exists():
        raise ValidationError("At least one opponent is required.")
    initial_ms = exhibition.clock_initial_minutes * 60 * 1000
    for seat in exhibition.seats.select_related("opponent"):
        white, black = (actor, seat.opponent) if exhibition.host_color == "white" else (seat.opponent, actor)
        seat.game = Game.objects.create(
            status=Game.Status.ACTIVE, white_user=white, black_user=black,
            white_display_name=white.display_name, black_display_name=black.display_name,
            clock_initial_ms=initial_ms, white_time_ms=initial_ms, black_time_ms=initial_ms,
            started_at=timezone.now(), last_move_at=timezone.now(), clock_started_at=timezone.now(),
            metadata={"mode": "simul", "simul_id": exhibition.pk, "board_number": seat.board_number},
        )
        seat.save(update_fields=["game", "updated_at"])
    exhibition.status = SimultaneousExhibition.Status.ACTIVE
    exhibition.save(update_fields=["status", "updated_at"])
    return exhibition


def recalculate_tiebreaks(tournament: Tournament) -> None:
    entries = {entry.pk: entry for entry in tournament.entries.all()}
    opponents = {entry_id: [] for entry_id in entries}
    for pairing in TournamentPairing.objects.filter(round__tournament=tournament).exclude(black_entry__isnull=True):
        opponents[pairing.white_entry_id].append((pairing.black_entry_id, pairing.result, "white"))
        opponents[pairing.black_entry_id].append((pairing.white_entry_id, pairing.result, "black"))
    for entry_id, entry in entries.items():
        entry.buchholz = sum((entries[opponent_id].score for opponent_id, _, _ in opponents[entry_id]), Decimal("0"))
        sb = Decimal("0")
        for opponent_id, result, color in opponents[entry_id]:
            won = (color == "white" and result == TournamentPairing.Result.WHITE_WIN) or (
                color == "black" and result == TournamentPairing.Result.BLACK_WIN
            )
            if won:
                sb += entries[opponent_id].score
            elif result == TournamentPairing.Result.DRAW:
                sb += entries[opponent_id].score * Decimal("0.5")
        entry.sonneborn_berger = sb
    TournamentEntry.objects.bulk_update(entries.values(), ["buchholz", "sonneborn_berger"])


@transaction.atomic
def join_tournament(*, tournament: Tournament, user: User) -> TournamentEntry:
    tournament = Tournament.objects.select_for_update().get(pk=tournament.pk)
    if tournament.status != Tournament.Status.REGISTRATION:
        raise ValidationError("Registration is closed.")
    existing = TournamentEntry.objects.filter(tournament=tournament, user=user).first()
    if existing:
        raise ValidationError("You are already registered.")
    if tournament.entries.count() >= tournament.max_players:
        raise ValidationError("This tournament is full.")
    entry = TournamentEntry.objects.create(tournament=tournament, user=user)
    if tournament.organizer_id != user.pk:
        notify(
            recipient=tournament.organizer,
            kind=Notification.Kind.TOURNAMENT,
            title=f"{user.display_name} joined {tournament.name}",
            target_url=tournament.get_absolute_url(),
        )
    return entry


def withdraw_from_tournament(*, tournament: Tournament, user: User) -> None:
    if tournament.status != Tournament.Status.REGISTRATION:
        raise ValidationError("You cannot withdraw after the tournament starts.")
    deleted, _ = TournamentEntry.objects.filter(tournament=tournament, user=user).delete()
    if not deleted:
        raise ValidationError("You are not registered for this tournament.")


@transaction.atomic
def start_tournament(*, tournament: Tournament, actor: User) -> Tournament:
    tournament = Tournament.objects.select_for_update().get(pk=tournament.pk)
    if tournament.organizer_id != actor.pk:
        raise PermissionDenied("Only the organizer can start this tournament.")
    if tournament.status != Tournament.Status.REGISTRATION:
        raise ValidationError("This tournament cannot be started.")
    entries = list(tournament.entries.select_related("user"))
    if len(entries) < 2:
        raise ValidationError("At least two players are required.")
    for seed, entry in enumerate(entries, start=1):
        entry.seed = seed
    TournamentEntry.objects.bulk_update(entries, ["seed"])
    tournament.status = Tournament.Status.ACTIVE
    tournament.save(update_fields=["status", "updated_at"])
    _create_next_round(tournament, 1)
    for entry in entries:
        notify(
            recipient=entry.user,
            kind=Notification.Kind.TOURNAMENT,
            title=f"{tournament.name} has started",
            target_url=tournament.get_absolute_url(),
        )
    return tournament


@transaction.atomic
def report_pairing_result(
    *,
    tournament: Tournament,
    pairing: TournamentPairing,
    actor: User,
    result: str,
) -> TournamentPairing:
    tournament = Tournament.objects.select_for_update().get(pk=tournament.pk)
    pairing = TournamentPairing.objects.select_for_update().select_related("round").get(pk=pairing.pk)
    if tournament.organizer_id != actor.pk:
        raise PermissionDenied("Only the organizer can report results.")
    if pairing.round.tournament_id != tournament.pk or tournament.status != Tournament.Status.ACTIVE:
        raise ValidationError("This pairing is not active in the tournament.")
    if pairing.result != TournamentPairing.Result.PENDING:
        raise ValidationError("This pairing already has a result.")
    if result not in {
        TournamentPairing.Result.WHITE_WIN,
        TournamentPairing.Result.BLACK_WIN,
        TournamentPairing.Result.DRAW,
    }:
        raise ValidationError("Select a valid result.")
    if pairing.black_entry_id is None:
        raise ValidationError("A bye result cannot be changed.")

    white_entry = TournamentEntry.objects.select_for_update().get(pk=pairing.white_entry_id)
    black_entry = TournamentEntry.objects.select_for_update().get(pk=pairing.black_entry_id)
    if result == TournamentPairing.Result.WHITE_WIN:
        white_entry.score += 1
    elif result == TournamentPairing.Result.BLACK_WIN:
        black_entry.score += 1
    else:
        white_entry.score += Decimal("0.5")
        black_entry.score += Decimal("0.5")
    TournamentEntry.objects.bulk_update([white_entry, black_entry], ["score"])
    pairing.result = result
    pairing.save(update_fields=["result", "updated_at"])
    tournament_round = pairing.round
    if not tournament_round.pairings.filter(result=TournamentPairing.Result.PENDING).exists():
        tournament_round.status = TournamentRound.Status.COMPLETED
        tournament_round.save(update_fields=["status", "updated_at"])
        recalculate_tiebreaks(tournament)
        if tournament_round.number >= _maximum_rounds(tournament, tournament.entries.count()):
            tournament.status = Tournament.Status.COMPLETED
            tournament.save(update_fields=["status", "updated_at"])
        else:
            _create_next_round(tournament, tournament_round.number + 1)
    return pairing


def sync_pairing_result_from_game(game: Game) -> None:
    """Advance a tournament automatically when its linked game finishes."""

    try:
        pairing = TournamentPairing.objects.select_related("round__tournament").get(game=game)
    except TournamentPairing.DoesNotExist:
        return
    if pairing.result != TournamentPairing.Result.PENDING or game.status != Game.Status.FINISHED:
        return
    result = {
        Game.Result.WHITE_WIN: TournamentPairing.Result.WHITE_WIN,
        Game.Result.BLACK_WIN: TournamentPairing.Result.BLACK_WIN,
        Game.Result.DRAW: TournamentPairing.Result.DRAW,
    }.get(game.result)
    if result:
        report_pairing_result(
            tournament=pairing.round.tournament,
            pairing=pairing,
            actor=pairing.round.tournament.organizer,
            result=result,
        )


def cancel_tournament(*, tournament: Tournament, actor: User) -> None:
    if tournament.organizer_id != actor.pk:
        raise PermissionDenied("Only the organizer can cancel this tournament.")
    if tournament.status in {Tournament.Status.COMPLETED, Tournament.Status.CANCELLED}:
        raise ValidationError("This tournament cannot be cancelled.")
    tournament.status = Tournament.Status.CANCELLED
    tournament.save(update_fields=["status", "updated_at"])
    for entry in tournament.entries.select_related("user").exclude(user=actor):
        notify(
            recipient=entry.user,
            kind=Notification.Kind.TOURNAMENT,
            title=f"{tournament.name} was cancelled",
            target_url=tournament.get_absolute_url(),
        )


def remove_tournament_player(*, tournament: Tournament, actor: User, entry: TournamentEntry) -> None:
    if tournament.organizer_id != actor.pk:
        raise PermissionDenied("Only the organizer can remove players.")
    if tournament.status != Tournament.Status.REGISTRATION:
        raise ValidationError("Players can only be removed before the tournament starts.")
    if entry.user_id == tournament.organizer_id:
        raise ValidationError("The organizer cannot be removed.")
    removed_user = entry.user
    entry.delete()
    notify(
        recipient=removed_user,
        kind=Notification.Kind.TOURNAMENT,
        title=f"You were removed from {tournament.name}",
        target_url=tournament.get_absolute_url(),
    )


def post_tournament_message(*, tournament: Tournament, actor: User, body: str) -> TournamentMessage:
    if actor.pk != tournament.organizer_id and not tournament.entries.filter(user=actor).exists():
        raise PermissionDenied("Join this tournament to use its chat.")
    body = body.strip()
    if not body:
        raise ValidationError("Message cannot be empty.")
    return TournamentMessage.objects.create(tournament=tournament, sender=actor, body=body[:500])


def post_tournament_announcement(*, tournament: Tournament, actor: User, body: str) -> TournamentAnnouncement:
    if actor.pk != tournament.organizer_id:
        raise PermissionDenied("Only the organizer can post announcements.")
    body = body.strip()
    if not body:
        raise ValidationError("Announcement cannot be empty.")
    announcement = TournamentAnnouncement.objects.create(tournament=tournament, author=actor, body=body[:500])
    for entry in tournament.entries.select_related("user").exclude(user=actor):
        notify(
            recipient=entry.user,
            kind=Notification.Kind.TOURNAMENT,
            title=f"New announcement in {tournament.name}",
            message=announcement.body,
            target_url=tournament.get_absolute_url(),
        )
    return announcement
