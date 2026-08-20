from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.core.models import TimeStampedModel

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class Game(TimeStampedModel):
    """Authoritative server-side chess game state."""

    class Variant(models.TextChoices):
        STANDARD = "standard", "Standard"

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        FINISHED = "finished", "Finished"
        ABORTED = "aborted", "Aborted"

    class Result(models.TextChoices):
        ONGOING = "*", "Ongoing"
        WHITE_WIN = "1-0", "White wins"
        BLACK_WIN = "0-1", "Black wins"
        DRAW = "1/2-1/2", "Draw"

    class Termination(models.TextChoices):
        NONE = "none", "None"
        CHECKMATE = "checkmate", "Checkmate"
        RESIGNATION = "resignation", "Resignation"
        AGREEMENT = "agreement", "Agreement"
        STALEMATE = "stalemate", "Stalemate"
        INSUFFICIENT_MATERIAL = "insufficient_material", "Insufficient material"
        SEVENTYFIVE_MOVES = "seventyfive_moves", "Seventy-five moves"
        FIVEFOLD_REPETITION = "fivefold_repetition", "Fivefold repetition"
        FIFTY_MOVE_RULE = "fifty_move_rule", "Fifty-move rule"
        THREEFOLD_REPETITION = "threefold_repetition", "Threefold repetition"
        TIMEOUT = "timeout", "Timeout"
        ABORTED = "aborted", "Aborted"
        IMPORTED = "imported", "Imported"
        ABANDONMENT = "abandonment", "Abandonment"

    class Color(models.TextChoices):
        WHITE = "white", "White"
        BLACK = "black", "Black"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.OneToOneField(
        "rooms.Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="game",
    )
    variant = models.CharField(max_length=24, choices=Variant.choices, default=Variant.STANDARD)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CREATED, db_index=True)
    rated = models.BooleanField(default=False, db_index=True)
    allow_spectators = models.BooleanField(default=True)

    white_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="white_games",
    )
    black_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="black_games",
    )
    white_guest_key = models.CharField(max_length=64, blank=True, db_index=True)
    black_guest_key = models.CharField(max_length=64, blank=True, db_index=True)
    white_display_name = models.CharField(max_length=80)
    black_display_name = models.CharField(max_length=80)

    initial_fen = models.CharField(max_length=150, default=STARTING_FEN)
    current_fen = models.CharField(max_length=150, default=STARTING_FEN)
    initial_pgn = models.TextField(blank=True)
    cached_pgn = models.TextField(blank=True)
    turn = models.CharField(max_length=5, choices=Color.choices, default=Color.WHITE, db_index=True)
    fullmove_number = models.PositiveIntegerField(default=1)
    ply_count = models.PositiveIntegerField(default=0, db_index=True)
    last_move_uci = models.CharField(max_length=8, blank=True)
    last_move_san = models.CharField(max_length=32, blank=True)

    clock_initial_ms = models.PositiveIntegerField(default=300000)
    increment_ms = models.PositiveIntegerField(default=0)
    delay_ms = models.PositiveIntegerField(default=0)
    white_time_ms = models.PositiveIntegerField(default=300000)
    black_time_ms = models.PositiveIntegerField(default=300000)
    clock_started_at = models.DateTimeField(null=True, blank=True)
    last_move_at = models.DateTimeField(null=True, blank=True)

    result = models.CharField(max_length=12, choices=Result.choices, default=Result.ONGOING, db_index=True)
    termination = models.CharField(max_length=32, choices=Termination.choices, default=Termination.NONE)
    winner_color = models.CharField(max_length=5, choices=Color.choices, blank=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True, db_index=True)

    draw_offer_by = models.CharField(max_length=5, choices=Color.choices, blank=True)
    draw_offer_at = models.DateTimeField(null=True, blank=True)
    takeback_offer_by = models.CharField(max_length=5, choices=Color.choices, blank=True)
    takeback_offer_at = models.DateTimeField(null=True, blank=True)
    offline_sync_id = models.UUIDField(null=True, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    white_rating_before = models.PositiveIntegerField(null=True, blank=True)
    black_rating_before = models.PositiveIntegerField(null=True, blank=True)
    white_rating_change = models.SmallIntegerField(default=0)
    black_rating_change = models.SmallIntegerField(default=0)
    ratings_applied = models.BooleanField(default=False)
    white_disconnected_at = models.DateTimeField(null=True, blank=True)
    black_disconnected_at = models.DateTimeField(null=True, blank=True)
    reconnect_grace_seconds = models.PositiveIntegerField(default=120)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="games_game_status_created_idx"),
            models.Index(fields=["rated", "status"], name="games_game_rated_status_idx"),
            models.Index(fields=["white_user", "created_at"], name="games_game_white_user_idx"),
            models.Index(fields=["black_user", "created_at"], name="games_game_black_user_idx"),
            models.Index(fields=["room"], name="games_game_room_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(clock_initial_ms__gte=0), name="games_clock_initial_nonnegative"),
            models.CheckConstraint(condition=Q(white_time_ms__gte=0), name="games_white_time_nonnegative"),
            models.CheckConstraint(condition=Q(black_time_ms__gte=0), name="games_black_time_nonnegative"),
            models.UniqueConstraint(
                fields=["white_user", "offline_sync_id"],
                condition=Q(offline_sync_id__isnull=False),
                name="games_user_offline_sync_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.white_display_name} vs {self.black_display_name}"

    def get_absolute_url(self) -> str:
        return reverse("games:play", kwargs={"pk": self.pk})

    @property
    def is_live(self) -> bool:
        return self.status == self.Status.ACTIVE

    @property
    def side_to_move(self) -> str:
        return self.turn

    def start(self) -> None:
        if self.status != self.Status.ACTIVE:
            now = timezone.now()
            self.status = self.Status.ACTIVE
            self.started_at = self.started_at or now
            self.clock_started_at = now
            self.last_move_at = now
            self.save(update_fields=["status", "started_at", "clock_started_at", "last_move_at", "updated_at"])

    def finish(self, *, result: str, termination: str, winner_color: str = "") -> None:
        self.status = self.Status.FINISHED if termination != self.Termination.ABORTED else self.Status.ABORTED
        self.result = result
        self.termination = termination
        self.winner_color = winner_color
        self.ended_at = timezone.now()
        self.clock_started_at = None
        self.draw_offer_by = ""
        self.draw_offer_at = None
        self.takeback_offer_by = ""
        self.takeback_offer_at = None
        self.save(
            update_fields=[
                "status",
                "result",
                "termination",
                "winner_color",
                "ended_at",
                "clock_started_at",
                "draw_offer_by",
                "draw_offer_at",
                "takeback_offer_by",
                "takeback_offer_at",
                "updated_at",
            ]
        )
        from apps.tournaments.services import sync_pairing_result_from_game

        sync_pairing_result_from_game(self)


class GameMove(TimeStampedModel):
    """Immutable move log used for replay, PGN generation, and recovery."""

    class Color(models.TextChoices):
        WHITE = "white", "White"
        BLACK = "black", "Black"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="moves")
    ply_number = models.PositiveIntegerField(db_index=True)
    move_number = models.PositiveIntegerField(db_index=True)
    color = models.CharField(max_length=5, choices=Color.choices, db_index=True)
    uci = models.CharField(max_length=8)
    san = models.CharField(max_length=32)
    from_square = models.CharField(max_length=2)
    to_square = models.CharField(max_length=2)
    promotion = models.CharField(max_length=1, blank=True)
    fen_before = models.CharField(max_length=150)
    fen_after = models.CharField(max_length=150)
    white_time_ms = models.PositiveIntegerField(default=0)
    black_time_ms = models.PositiveIntegerField(default=0)
    played_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="played_moves",
    )
    played_by_guest_key = models.CharField(max_length=64, blank=True)
    played_by_display_name = models.CharField(max_length=80, blank=True)
    client_lag_ms = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ply_number"]
        indexes = [
            models.Index(fields=["game", "ply_number"], name="games_move_game_ply_idx"),
            models.Index(fields=["game", "move_number"], name="games_move_game_move_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["game", "ply_number"], name="games_unique_ply_per_game"),
        ]

    def __str__(self) -> str:
        return f"{self.game_id} {self.move_number}. {self.san}"


class GameEvent(TimeStampedModel):
    """Append-only game event log for realtime recovery and moderation."""

    class EventType(models.TextChoices):
        CREATED = "game.created", "Game created"
        STARTED = "game.started", "Game started"
        MOVE = "move.played", "Move played"
        RESIGN = "game.resigned", "Game resigned"
        ABORT = "game.aborted", "Game aborted"
        DRAW_OFFER = "draw.offered", "Draw offered"
        DRAW_ACCEPT = "draw.accepted", "Draw accepted"
        DRAW_DECLINE = "draw.declined", "Draw declined"
        TAKEBACK_OFFER = "takeback.offered", "Takeback offered"
        TAKEBACK_ACCEPT = "takeback.accepted", "Takeback accepted"
        TAKEBACK_DECLINE = "takeback.declined", "Takeback declined"
        CLOCK_TIMEOUT = "clock.timeout", "Clock timeout"
        CHAT = "game.chat", "Game chat"
        ERROR = "game.error", "Game error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=64, choices=EventType.choices, db_index=True)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="game_events",
    )
    actor_guest_key = models.CharField(max_length=64, blank=True, db_index=True)
    actor_display_name = models.CharField(max_length=80, blank=True)
    actor_color = models.CharField(max_length=5, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["game", "event_type", "created_at"], name="games_event_game_type_idx"),
            models.Index(fields=["game", "created_at"], name="games_event_game_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} {self.game_id}"


class GameChatMessage(TimeStampedModel):
    class Audience(models.TextChoices):
        ALL = "all", "Everyone"
        PLAYERS = "players", "Players"
        SPECTATORS = "spectators", "Spectators"

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="chat_messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    sender_name = models.CharField(max_length=80)
    sender_role = models.CharField(max_length=16, default="spectator")
    body = models.CharField(max_length=500)
    audience = models.CharField(max_length=16, choices=Audience.choices, default=Audience.ALL)
    is_removed = models.BooleanField(default=False, db_index=True)
    reports = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["game", "created_at"], name="game_chat_game_time_idx")]


class FairPlayReview(TimeStampedModel):
    class Status(models.TextChoices):
        CLEAR = "clear", "Clear"
        FLAGGED = "flagged", "Flagged"
        REVIEWING = "reviewing", "Reviewing"
        CONFIRMED = "confirmed", "Confirmed violation"
        DISMISSED = "dismissed", "Dismissed"

    game = models.OneToOneField(Game, on_delete=models.CASCADE, related_name="fair_play_review")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CLEAR, db_index=True)
    risk_score = models.PositiveSmallIntegerField(default=0, db_index=True)
    white_engine_match_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    black_engine_match_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    white_avg_loss_cp = models.PositiveIntegerField(default=0)
    black_avg_loss_cp = models.PositiveIntegerField(default=0)
    signals = models.JSONField(default=list, blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="fair_play_reviews"
    )
    moderator_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)


class FairPlayAppeal(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REVIEWING = "reviewing", "Reviewing"
        UPHELD = "upheld", "Decision upheld"
        OVERTURNED = "overturned", "Decision overturned"

    review = models.ForeignKey(FairPlayReview, on_delete=models.CASCADE, related_name="appeals")
    appellant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fair_play_appeals")
    statement = models.TextField(max_length=4000)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    moderator_response = models.TextField(blank=True, max_length=4000)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fair_play_appeals_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["review", "appellant"], name="games_unique_fair_play_appeal")]
