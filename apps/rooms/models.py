from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.rooms.managers import RoomManager
from apps.rooms.services import generate_room_code


class Room(TimeStampedModel):
    """A pre-game lobby that can work online, offline, or over LAN."""

    class Mode(models.TextChoices):
        ONLINE = "online", "Online"
        LAN = "lan", "LAN"
        OFFLINE = "offline", "Offline"
        SAME_PC = "same_pc", "Same computer"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"
        INVITE_ONLY = "invite_only", "Invite only"

    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        READY = "ready", "Ready"
        IN_PROGRESS = "in_progress", "In progress"
        FINISHED = "finished", "Finished"
        ABORTED = "aborted", "Aborted"
        EXPIRED = "expired", "Expired"

    class TimeCategory(models.TextChoices):
        BULLET = "bullet", "Bullet"
        BLITZ = "blitz", "Blitz"
        RAPID = "rapid", "Rapid"
        CLASSICAL = "classical", "Classical"
        DAILY = "daily", "Daily"
        CUSTOM = "custom", "Custom"

    class ColorPreference(models.TextChoices):
        RANDOM = "random", "Random"
        WHITE = "white", "White"
        BLACK = "black", "Black"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=12, unique=True, db_index=True)
    name = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=240, blank=True)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hosted_rooms",
    )
    host_guest_key = models.CharField(max_length=64, blank=True, db_index=True)
    host_display_name = models.CharField(max_length=80, blank=True)
    mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.ONLINE, db_index=True)
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.WAITING, db_index=True)
    rated = models.BooleanField(default=False)
    allow_guests = models.BooleanField(default=True)
    spectator_enabled = models.BooleanField(default=True)
    max_players = models.PositiveSmallIntegerField(default=2)
    time_category = models.CharField(
        max_length=16, choices=TimeCategory.choices, default=TimeCategory.BLITZ, db_index=True
    )
    clock_initial_seconds = models.PositiveIntegerField(default=300)
    increment_seconds = models.PositiveSmallIntegerField(default=0)
    delay_seconds = models.PositiveSmallIntegerField(default=0)
    color_preference = models.CharField(max_length=10, choices=ColorPreference.choices, default=ColorPreference.RANDOM)
    private_note = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    last_activity_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = RoomManager()

    class Meta:
        ordering = ["-last_activity_at", "-created_at"]
        indexes = [
            models.Index(fields=["code"], name="rooms_room_code_idx"),
            models.Index(fields=["mode", "status"], name="rooms_room_mode_status_idx"),
            models.Index(fields=["visibility", "status"], name="rooms_room_visible_status_idx"),
            models.Index(fields=["time_category", "rated"], name="rooms_room_time_rated_idx"),
            models.Index(fields=["last_activity_at"], name="rooms_room_last_activity_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="rooms_room_code_unique"),
            models.CheckConstraint(condition=Q(max_players__gte=2), name="rooms_room_min_players"),
            models.CheckConstraint(condition=Q(clock_initial_seconds__gte=0), name="rooms_room_clock_nonnegative"),
        ]

    def __str__(self) -> str:
        return self.name or f"Room {self.code}"

    def save(self, *args, **kwargs) -> None:
        if not self.code:
            self.code = generate_room_code()
        if not self.name:
            self.name = f"Chess Room {self.code}"
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("rooms:detail", kwargs={"code": self.code})

    @property
    def invite_path(self) -> str:
        return self.get_absolute_url()

    @property
    def is_joinable(self) -> bool:
        return self.status in {self.Status.WAITING, self.Status.READY}

    @property
    def time_control_label(self) -> str:
        minutes = self.clock_initial_seconds // 60
        seconds = self.clock_initial_seconds % 60
        base = (
            f"{minutes}+{self.increment_seconds}"
            if seconds == 0
            else f"{minutes}:{seconds:02d}+{self.increment_seconds}"
        )
        if self.delay_seconds:
            return f"{base} delay {self.delay_seconds}s"
        return base

    def touch(self) -> None:
        self.last_activity_at = timezone.now()
        self.save(update_fields=["last_activity_at", "updated_at"])


class RoomParticipant(TimeStampedModel):
    """A person occupying a room as host, player, or spectator."""

    class Role(models.TextChoices):
        HOST = "host", "Host"
        PLAYER = "player", "Player"
        SPECTATOR = "spectator", "Spectator"

    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        JOINED = "joined", "Joined"
        READY = "ready", "Ready"
        LEFT = "left", "Left"
        KICKED = "kicked", "Kicked"

    class Side(models.TextChoices):
        WHITE = "white", "White"
        BLACK = "black", "Black"
        RANDOM = "random", "Random"
        NONE = "none", "None"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="room_participations",
    )
    guest_key = models.CharField(max_length=64, blank=True, db_index=True)
    display_name = models.CharField(max_length=80)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PLAYER, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.JOINED, db_index=True)
    side = models.CharField(max_length=8, choices=Side.choices, default=Side.RANDOM)
    is_connected = models.BooleanField(default=False, db_index=True)
    connection_count = models.PositiveSmallIntegerField(default=0)
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["role", "joined_at"]
        indexes = [
            models.Index(fields=["room", "role", "status"], name="rooms_participant_role_idx"),
            models.Index(fields=["room", "is_connected"], name="rooms_participant_presence_idx"),
            models.Index(fields=["guest_key"], name="rooms_participant_guest_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["room", "user"],
                condition=Q(user__isnull=False),
                name="rooms_unique_user_per_room",
            ),
            models.UniqueConstraint(
                fields=["room", "guest_key"],
                condition=~Q(guest_key=""),
                name="rooms_unique_guest_per_room",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} in {self.room.code}"

    @property
    def is_player(self) -> bool:
        return self.role in {self.Role.HOST, self.Role.PLAYER}

    def mark_connected(self) -> None:
        self.connection_count += 1
        self.is_connected = True
        self.last_seen_at = timezone.now()
        if self.status == self.Status.LEFT:
            self.status = self.Status.JOINED
            self.left_at = None
        self.save(update_fields=["connection_count", "is_connected", "last_seen_at", "status", "left_at", "updated_at"])

    def mark_disconnected(self) -> None:
        self.connection_count = max(self.connection_count - 1, 0)
        self.is_connected = self.connection_count > 0
        self.last_seen_at = timezone.now()
        self.save(update_fields=["connection_count", "is_connected", "last_seen_at", "updated_at"])

    def mark_ready(self, ready: bool) -> None:
        self.status = self.Status.READY if ready else self.Status.JOINED
        self.last_seen_at = timezone.now()
        self.save(update_fields=["status", "last_seen_at", "updated_at"])

    def leave(self) -> None:
        self.status = self.Status.LEFT
        self.left_at = timezone.now()
        self.is_connected = False
        self.connection_count = 0
        self.last_seen_at = timezone.now()
        self.save(update_fields=["status", "left_at", "is_connected", "connection_count", "last_seen_at", "updated_at"])


class RoomEvent(TimeStampedModel):
    """Append-only room event log for recovery, audit, and replay."""

    class EventType(models.TextChoices):
        ROOM_CREATED = "room.created", "Room created"
        PARTICIPANT_JOINED = "participant.joined", "Participant joined"
        PARTICIPANT_LEFT = "participant.left", "Participant left"
        PARTICIPANT_READY = "participant.ready", "Participant ready"
        CHAT_MESSAGE = "chat.message", "Chat message"
        ROOM_UPDATED = "room.updated", "Room updated"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=64, choices=EventType.choices, db_index=True)
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="room_events",
    )
    actor_guest_key = models.CharField(max_length=64, blank=True, db_index=True)
    actor_display_name = models.CharField(max_length=80, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["room", "event_type", "created_at"], name="rooms_event_room_type_idx"),
            models.Index(fields=["room", "created_at"], name="rooms_event_room_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} {self.room.code}"
