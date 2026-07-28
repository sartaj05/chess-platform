from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class StockfishEngineProfile(TimeStampedModel):
    """Named Stockfish configuration used by analysis jobs."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)
    binary_path = models.CharField(max_length=500, default="/usr/games/stockfish")
    default_depth = models.PositiveSmallIntegerField(default=12)
    default_movetime_ms = models.PositiveIntegerField(default=750)
    skill_level = models.PositiveSmallIntegerField(default=20)
    threads = models.PositiveSmallIntegerField(default=1)
    hash_mb = models.PositiveIntegerField(default=64)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active", "name"], name="stockfish_profile_active_idx")]
        constraints = [
            models.CheckConstraint(condition=Q(default_depth__gte=1), name="stockfish_depth_min_one"),
            models.CheckConstraint(condition=Q(skill_level__lte=20), name="stockfish_skill_max_twenty"),
            models.CheckConstraint(condition=Q(threads__gte=1), name="stockfish_threads_min_one"),
            models.CheckConstraint(condition=Q(hash_mb__gte=1), name="stockfish_hash_min_one"),
        ]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def default_profile(cls) -> StockfishEngineProfile:
        profile, _created = cls.objects.get_or_create(
            name="Default Offline Stockfish",
            defaults={
                "binary_path": getattr(settings, "STOCKFISH_BINARY", "/usr/games/stockfish"),
                "default_depth": getattr(settings, "STOCKFISH_DEFAULT_DEPTH", 12),
                "default_movetime_ms": getattr(settings, "STOCKFISH_DEFAULT_MOVETIME_MS", 750),
                "threads": getattr(settings, "STOCKFISH_THREADS", 1),
                "hash_mb": getattr(settings, "STOCKFISH_HASH_MB", 64),
                "is_active": True,
            },
        )
        return profile


class StockfishRun(TimeStampedModel):
    """Auditable record of a single UCI engine request."""

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        UNAVAILABLE = "unavailable", "Unavailable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        StockfishEngineProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="runs"
    )
    game = models.ForeignKey("games.Game", on_delete=models.SET_NULL, null=True, blank=True, related_name="engine_runs")
    fen = models.CharField(max_length=180)
    command_type = models.CharField(max_length=40, default="position_analysis")
    depth = models.PositiveSmallIntegerField(default=0)
    movetime_ms = models.PositiveIntegerField(default=0)
    bestmove = models.CharField(max_length=8, blank=True)
    ponder = models.CharField(max_length=8, blank=True)
    score_cp = models.IntegerField(null=True, blank=True)
    mate_score = models.IntegerField(null=True, blank=True)
    nodes = models.BigIntegerField(default=0)
    nps = models.BigIntegerField(default=0)
    raw_info = models.JSONField(default=dict, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS, db_index=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="stockfish_run_status_time_idx"),
            models.Index(fields=["game", "created_at"], name="stockfish_run_game_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.command_type} {self.status} {self.bestmove or '-'}"
