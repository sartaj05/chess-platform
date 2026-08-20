from __future__ import annotations

import secrets
import string

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse

from apps.core.models import TimeStampedModel


class Tournament(TimeStampedModel):
    class Status(models.TextChoices):
        REGISTRATION = "registration", "Registration open"
        ACTIVE = "active", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Format(models.TextChoices):
        SWISS = "swiss", "Swiss"
        ROUND_ROBIN = "round_robin", "Round robin"
        KNOCKOUT = "knockout", "Knockout"

    name = models.CharField(max_length=120)
    description = models.TextField(max_length=1000, blank=True)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organized_tournaments")
    format = models.CharField(max_length=20, choices=Format.choices, default=Format.SWISS)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REGISTRATION, db_index=True)
    starts_at = models.DateTimeField(db_index=True)
    max_players = models.PositiveSmallIntegerField(default=16)
    clock_initial_minutes = models.PositiveSmallIntegerField(default=10)
    increment_seconds = models.PositiveSmallIntegerField(default=0)
    is_public = models.BooleanField(default=True, db_index=True)
    invite_code = models.CharField(max_length=8, unique=True, editable=False, db_index=True)

    class Meta:
        ordering = ["starts_at", "name"]
        constraints = [
            models.CheckConstraint(condition=Q(max_players__gte=2), name="tournament_min_capacity"),
            models.CheckConstraint(condition=Q(clock_initial_minutes__gte=1), name="tournament_positive_clock"),
        ]
        indexes = [models.Index(fields=["is_public", "status", "starts_at"], name="tournament_public_status_idx")]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.invite_code:
            alphabet = string.ascii_uppercase + string.digits
            while True:
                candidate = "".join(secrets.choice(alphabet) for _ in range(8))
                if not type(self).objects.filter(invite_code=candidate).exists():
                    self.invite_code = candidate
                    break
        return super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("tournaments:detail", kwargs={"pk": self.pk})

    @property
    def time_control(self) -> str:
        return f"{self.clock_initial_minutes}+{self.increment_seconds}"


class TournamentEntry(TimeStampedModel):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="entries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tournament_entries")
    seed = models.PositiveSmallIntegerField(blank=True, null=True)
    score = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        ordering = ["-score", "seed", "created_at"]
        constraints = [models.UniqueConstraint(fields=["tournament", "user"], name="tournament_unique_player")]

    def __str__(self) -> str:
        return f"{self.user} in {self.tournament}"


class TournamentRound(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "In progress"
        COMPLETED = "completed", "Completed"

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="rounds")
    number = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        ordering = ["number"]
        constraints = [models.UniqueConstraint(fields=["tournament", "number"], name="tournament_unique_round")]

    def __str__(self) -> str:
        return f"{self.tournament} - Round {self.number}"


class TournamentPairing(TimeStampedModel):
    class Result(models.TextChoices):
        PENDING = "pending", "Pending"
        WHITE_WIN = "white_win", "White wins"
        BLACK_WIN = "black_win", "Black wins"
        DRAW = "draw", "Draw"
        BYE = "bye", "Bye"

    round = models.ForeignKey(TournamentRound, on_delete=models.CASCADE, related_name="pairings")
    board_number = models.PositiveSmallIntegerField()
    white_entry = models.ForeignKey(TournamentEntry, on_delete=models.CASCADE, related_name="pairings_as_white")
    black_entry = models.ForeignKey(
        TournamentEntry,
        on_delete=models.CASCADE,
        related_name="pairings_as_black",
        blank=True,
        null=True,
    )
    result = models.CharField(max_length=16, choices=Result.choices, default=Result.PENDING, db_index=True)

    class Meta:
        ordering = ["round__number", "board_number"]
        constraints = [models.UniqueConstraint(fields=["round", "board_number"], name="tournament_unique_board")]

    def __str__(self) -> str:
        opponent = self.black_entry.user if self.black_entry_id else "Bye"
        return f"Board {self.board_number}: {self.white_entry.user} vs {opponent}"
