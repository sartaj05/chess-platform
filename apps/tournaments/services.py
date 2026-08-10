from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Tournament, TournamentEntry, TournamentPairing, TournamentRound


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
    tournament_round = TournamentRound.objects.create(tournament=tournament, number=1)
    board_number = 1
    for index in range(0, len(entries), 2):
        white_entry = entries[index]
        black_entry = entries[index + 1] if index + 1 < len(entries) else None
        pairing = TournamentPairing.objects.create(
            round=tournament_round,
            board_number=board_number,
            white_entry=white_entry,
            black_entry=black_entry,
            result=TournamentPairing.Result.PENDING if black_entry else TournamentPairing.Result.BYE,
        )
        if pairing.result == TournamentPairing.Result.BYE:
            white_entry.score += 1
            white_entry.save(update_fields=["score", "updated_at"])
        board_number += 1
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
    return pairing
