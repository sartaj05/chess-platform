from __future__ import annotations

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

    class Meta:
        ordering = ["starts_at", "name"]
        constraints = [
            models.CheckConstraint(condition=Q(max_players__gte=2), name="tournament_min_capacity"),
            models.CheckConstraint(condition=Q(clock_initial_minutes__gte=1), name="tournament_positive_clock"),
        ]
        indexes = [models.Index(fields=["is_public", "status", "starts_at"], name="tournament_public_status_idx")]

    def __str__(self) -> str:
        return self.name

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
