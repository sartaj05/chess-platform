from __future__ import annotations

import math
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import (
    Tournament,
    TournamentAnnouncement,
    TournamentEntry,
    TournamentMessage,
    TournamentPairing,
    TournamentRound,
)


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
        board += 1
    return tournament_round


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
