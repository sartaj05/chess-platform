from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Tournament, TournamentEntry


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
    for entry in entries:
        notify(
            recipient=entry.user,
            kind=Notification.Kind.TOURNAMENT,
            title=f"{tournament.name} has started",
            target_url=tournament.get_absolute_url(),
        )
    return tournament
