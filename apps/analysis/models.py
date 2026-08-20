from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.core.models import TimeStampedModel


class GameAnalysisJob(TimeStampedModel):
    """Asynchronous full-game review job."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class AnalysisType(models.TextChoices):
        QUICK = "quick", "Quick"
        DEEP = "deep", "Deep"
        IMPORTED = "imported", "Imported"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.CASCADE,
        related_name="analysis_jobs",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analysis_jobs",
    )
    engine_profile = models.ForeignKey(
        "stockfish.StockfishEngineProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analysis_jobs",
    )
    analysis_type = models.CharField(
        max_length=20,
        choices=AnalysisType.choices,
        default=AnalysisType.QUICK,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    depth = models.PositiveSmallIntegerField(default=10)
    movetime_ms = models.PositiveIntegerField(default=500)
    progress = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["game", "status"],
                name="an_job_gs_idx",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="an_job_st_time_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(depth__gte=1), name="analysis_depth_min_one"),
            models.CheckConstraint(condition=Q(progress__lte=100), name="analysis_progress_max_100"),
        ]

    def __str__(self) -> str:
        return f"{self.game_id} {self.analysis_type} {self.status}"

    def get_absolute_url(self) -> str:
        return reverse("analysis:job_detail", kwargs={"pk": self.pk})

    def mark_running(self) -> None:
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.error_message = ""
        self.save(update_fields=["status", "started_at", "error_message", "updated_at"])

    def mark_completed(self, *, summary: dict) -> None:
        self.status = self.Status.COMPLETED
        self.progress = 100
        self.summary = summary
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "progress", "summary", "completed_at", "updated_at"])

    def mark_failed(self, message: str) -> None:
        self.status = self.Status.FAILED
        self.error_message = message[:4000]
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at", "updated_at"])


class PositionAnalysis(TimeStampedModel):
    """Single-position engine result used by board analysis and review."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        GameAnalysisJob,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="positions",
    )
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="position_analyses",
    )
    move = models.ForeignKey(
        "games.GameMove",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="position_analyses",
    )
    fen = models.CharField(max_length=180, db_index=True)
    side_to_move = models.CharField(max_length=5, db_index=True)
    depth = models.PositiveSmallIntegerField(default=0)
    movetime_ms = models.PositiveIntegerField(default=0)
    multipv = models.PositiveSmallIntegerField(default=1)
    bestmove_uci = models.CharField(max_length=8, blank=True)
    bestmove_san = models.CharField(max_length=32, blank=True)
    score_cp = models.IntegerField(null=True, blank=True)
    score_white_cp = models.IntegerField(null=True, blank=True)
    mate_score = models.IntegerField(null=True, blank=True)
    pv = models.JSONField(default=list, blank=True)
    raw_engine = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["game", "created_at"], name="an_pos_gc_idx"),
            models.Index(fields=["job", "created_at"], name="an_pos_jc_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.bestmove_uci or '-'} {self.score_white_cp}"


class MoveReview(TimeStampedModel):
    """Human-readable classification for a played move."""

    class Classification(models.TextChoices):
        BOOK = "book", "Book"
        BEST = "best", "Best"
        EXCELLENT = "excellent", "Excellent"
        GOOD = "good", "Good"
        INACCURACY = "inaccuracy", "Inaccuracy"
        MISTAKE = "mistake", "Mistake"
        BLUNDER = "blunder", "Blunder"
        FORCED = "forced", "Forced"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        GameAnalysisJob,
        on_delete=models.CASCADE,
        related_name="move_reviews",
    )
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.CASCADE,
        related_name="move_reviews",
    )
    move = models.ForeignKey(
        "games.GameMove",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    ply_number = models.PositiveIntegerField(db_index=True)
    move_uci = models.CharField(max_length=8)
    move_san = models.CharField(max_length=32)
    classification = models.CharField(max_length=20, choices=Classification.choices, db_index=True)
    before_score_white_cp = models.IntegerField(null=True, blank=True)
    after_score_white_cp = models.IntegerField(null=True, blank=True)
    bestmove_uci = models.CharField(max_length=8, blank=True)
    bestmove_san = models.CharField(max_length=32, blank=True)
    score_loss_cp = models.PositiveIntegerField(default=0)
    comment = models.CharField(max_length=255, blank=True)
    best_line = models.JSONField(default=list, blank=True)
    fen_before = models.CharField(max_length=180)
    fen_after = models.CharField(max_length=180)

    class Meta:
        ordering = ["ply_number"]
        indexes = [
            models.Index(fields=["game", "ply_number"], name="an_rev_gp_idx"),
            models.Index(fields=["classification", "created_at"], name="an_rev_cl_time"),
        ]
        constraints = [models.UniqueConstraint(fields=["job", "ply_number"], name="analysis_unique_review_job_ply")]

    def __str__(self) -> str:
        return f"{self.move_san} {self.classification}"


class OpeningBookLine(TimeStampedModel):
    """Small local opening explorer seed, extendable from PGN imports later."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    eco = models.CharField(max_length=8, db_index=True)
    name = models.CharField(max_length=160, db_index=True)
    moves_uci = models.JSONField(default=list)
    moves_san = models.CharField(max_length=500)
    pgn_prefix = models.CharField(max_length=500, db_index=True)
    fen_after = models.CharField(max_length=180)
    frequency = models.PositiveIntegerField(default=1)
    white_win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    draw_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    black_win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["eco", "name"]
        indexes = [
            models.Index(fields=["is_active", "eco"], name="an_open_eco_idx"),
            models.Index(fields=["is_active", "name"], name="an_open_name_idx"),
        ]
        constraints = [models.UniqueConstraint(fields=["eco", "pgn_prefix"], name="analysis_unique_eco_prefix")]

    def __str__(self) -> str:
        return f"{self.eco} {self.name}"


class OpeningExplorerQuery(TimeStampedModel):
    """Usage log for opening explorer requests."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opening_queries",
    )
    moves_uci = models.JSONField(default=list, blank=True)
    fen = models.CharField(max_length=180, blank=True)
    result_count = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"], name="an_open_qtime_idx"),
        ]


class OpeningPractice(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="opening_practice")
    opening = models.ForeignKey(OpeningBookLine, on_delete=models.CASCADE, related_name="practice_records")
    interval_days = models.PositiveSmallIntegerField(default=1)
    ease_factor = models.DecimalField(max_digits=3, decimal_places=2, default=2.50)
    repetitions = models.PositiveSmallIntegerField(default=0)
    due_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_quality = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["due_at"]
        constraints = [models.UniqueConstraint(fields=["user", "opening"], name="opening_practice_user_line")]
