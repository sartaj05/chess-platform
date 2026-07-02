from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone

ROOM_CODE_ALPHABET = string.ascii_uppercase + string.digits
GUEST_SESSION_KEY = "chess_guest_key"
GUEST_NAME_SESSION_KEY = "chess_guest_display_name"


@dataclass(frozen=True)
class ParticipantIdentity:
    """Resolved authenticated or guest identity for room operations."""

    user: Any | None
    guest_key: str
    display_name: str


def generate_room_code(length: int = 8) -> str:
    """Generate a human-friendly room code without ambiguous lowercase letters."""

    from apps.rooms.models import Room

    for _ in range(50):
        code = "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(length))
        if not Room.objects.filter(code=code).exists():
            return code
    return secrets.token_urlsafe(9).upper().replace("-", "")[:12]


def ensure_guest_identity(request: HttpRequest, display_name: str | None = None) -> ParticipantIdentity:
    """Create or reuse a guest identity stored in the Django session."""

    user = request.user if getattr(request, "user", None) is not None and request.user.is_authenticated else None
    if user is not None:
        return ParticipantIdentity(user=user, guest_key="", display_name=user.display_name or user.email)

    guest_key = request.session.get(GUEST_SESSION_KEY)
    if not guest_key:
        guest_key = secrets.token_urlsafe(24)
        request.session[GUEST_SESSION_KEY] = guest_key

    clean_name = (display_name or request.session.get(GUEST_NAME_SESSION_KEY) or "").strip()[:80]
    if not clean_name:
        clean_name = f"Guest-{guest_key[:5].upper()}"
    request.session[GUEST_NAME_SESSION_KEY] = clean_name
    request.session.modified = True
    return ParticipantIdentity(user=None, guest_key=guest_key, display_name=clean_name)


def identity_from_scope(scope: dict[str, Any]) -> ParticipantIdentity:
    """Resolve room identity inside a Channels consumer scope."""

    user = scope.get("user")
    if user is not None and getattr(user, "is_authenticated", False):
        return ParticipantIdentity(user=user, guest_key="", display_name=user.display_name or user.email)

    session = scope.get("session")
    guest_key = ""
    display_name = "Guest"
    if session is not None:
        guest_key = session.get(GUEST_SESSION_KEY, "")
        display_name = session.get(GUEST_NAME_SESSION_KEY, "") or "Guest"
    if not guest_key:
        guest_key = secrets.token_urlsafe(24)
    if display_name == "Guest":
        display_name = f"Guest-{guest_key[:5].upper()}"
    return ParticipantIdentity(user=None, guest_key=guest_key, display_name=display_name[:80])


def absolute_invite_url(request: HttpRequest, room: Any) -> str:
    """Return an absolute URL usable on VPS or LAN host."""

    return request.build_absolute_uri(reverse("rooms:detail", kwargs={"code": room.code}))


def classify_time_category(initial_seconds: int, increment_seconds: int) -> str:
    """Classify chess time controls into common categories."""

    from apps.rooms.models import Room

    total_estimated = initial_seconds + 40 * increment_seconds
    if initial_seconds >= 86400:
        return Room.TimeCategory.DAILY
    if total_estimated < 180:
        return Room.TimeCategory.BULLET
    if total_estimated < 600:
        return Room.TimeCategory.BLITZ
    if total_estimated < 3600:
        return Room.TimeCategory.RAPID
    return Room.TimeCategory.CLASSICAL


@transaction.atomic
def create_room(*, request: HttpRequest, cleaned_data: dict[str, Any]):
    """Create a room and host participant in a single transaction."""

    from apps.rooms.models import Room, RoomEvent, RoomParticipant

    identity = ensure_guest_identity(request, cleaned_data.get("host_display_name"))
    initial_minutes = int(cleaned_data.get("clock_initial_minutes") or 5)
    initial_seconds = initial_minutes * 60
    increment_seconds = int(cleaned_data.get("increment_seconds") or 0)
    delay_seconds = int(cleaned_data.get("delay_seconds") or 0)
    room = Room.objects.create_room(
        name=cleaned_data.get("name", "")[:120],
        description=cleaned_data.get("description", "")[:240],
        host=identity.user,
        host_guest_key=identity.guest_key,
        host_display_name=identity.display_name,
        mode=cleaned_data.get("mode") or Room.Mode.ONLINE,
        visibility=cleaned_data.get("visibility") or Room.Visibility.PRIVATE,
        rated=bool(cleaned_data.get("rated")),
        allow_guests=bool(cleaned_data.get("allow_guests")),
        spectator_enabled=bool(cleaned_data.get("spectator_enabled")),
        clock_initial_seconds=initial_seconds,
        increment_seconds=increment_seconds,
        delay_seconds=delay_seconds,
        time_category=classify_time_category(initial_seconds, increment_seconds),
        color_preference=cleaned_data.get("color_preference") or Room.ColorPreference.RANDOM,
    )
    RoomParticipant.objects.create(
        room=room,
        user=identity.user,
        guest_key=identity.guest_key,
        display_name=identity.display_name,
        role=RoomParticipant.Role.HOST,
        side=RoomParticipant.Side.RANDOM,
    )
    RoomEvent.objects.create(
        room=room,
        event_type=RoomEvent.EventType.ROOM_CREATED,
        actor_user=identity.user,
        actor_guest_key=identity.guest_key,
        actor_display_name=identity.display_name,
        payload={"mode": room.mode, "visibility": room.visibility, "time_control": room.time_control_label},
    )
    return room


@transaction.atomic
def join_room(*, request: HttpRequest, room: Any, display_name: str | None = None, as_spectator: bool = False):
    """Join an existing room as player or spectator."""

    from apps.rooms.models import RoomEvent, RoomParticipant

    if not room.is_joinable:
        raise ValidationError("This room is not accepting new players.")

    identity = ensure_guest_identity(request, display_name)
    if identity.user is None and not room.allow_guests:
        raise PermissionDenied("Guests are not allowed in this room.")

    active_players = room.participants.filter(
        role__in=[RoomParticipant.Role.HOST, RoomParticipant.Role.PLAYER],
        status__in=[RoomParticipant.Status.JOINED, RoomParticipant.Status.READY],
    ).count()
    role = RoomParticipant.Role.SPECTATOR if as_spectator else RoomParticipant.Role.PLAYER
    if not as_spectator and active_players >= room.max_players:
        if room.spectator_enabled:
            role = RoomParticipant.Role.SPECTATOR
        else:
            raise ValidationError("The room is full.")
    if as_spectator and not room.spectator_enabled:
        raise ValidationError("Spectators are disabled for this room.")

    filters = {"room": room}
    if identity.user is not None:
        filters["user"] = identity.user
    else:
        filters["guest_key"] = identity.guest_key

    participant, created = RoomParticipant.objects.get_or_create(
        defaults={"display_name": identity.display_name, "role": role, "side": RoomParticipant.Side.RANDOM},
        **filters,
    )
    changed_fields: list[str] = []
    if participant.status == RoomParticipant.Status.LEFT:
        participant.status = RoomParticipant.Status.JOINED
        participant.left_at = None
        changed_fields.extend(["status", "left_at"])
    if display_name and participant.display_name != identity.display_name:
        participant.display_name = identity.display_name
        changed_fields.append("display_name")
    if participant.role != RoomParticipant.Role.HOST and participant.role != role:
        participant.role = role
        changed_fields.append("role")
    if changed_fields:
        changed_fields.append("updated_at")
        participant.save(update_fields=changed_fields)

    room.touch()
    if created:
        RoomEvent.objects.create(
            room=room,
            event_type=RoomEvent.EventType.PARTICIPANT_JOINED,
            actor_user=identity.user,
            actor_guest_key=identity.guest_key,
            actor_display_name=identity.display_name,
            payload={"role": participant.role},
        )
    return participant


def serialize_participant(participant: Any) -> dict[str, Any]:
    """Return safe participant information for templates, API, and websockets."""

    return {
        "id": str(participant.id),
        "display_name": participant.display_name,
        "role": participant.role,
        "status": participant.status,
        "side": participant.side,
        "is_connected": participant.is_connected,
        "is_authenticated": participant.user_id is not None,
        "last_seen_at": participant.last_seen_at.isoformat() if participant.last_seen_at else None,
    }


def serialize_room(room: Any, *, request: HttpRequest | None = None) -> dict[str, Any]:
    """Serialize room state without exposing internal guest tokens."""

    participants = [serialize_participant(item) for item in room.participants.all().order_by("role", "joined_at")]
    payload = {
        "id": str(room.id),
        "code": room.code,
        "name": room.name,
        "description": room.description,
        "mode": room.mode,
        "visibility": room.visibility,
        "status": room.status,
        "rated": room.rated,
        "allow_guests": room.allow_guests,
        "spectator_enabled": room.spectator_enabled,
        "max_players": room.max_players,
        "time_category": room.time_category,
        "time_control": room.time_control_label,
        "clock_initial_seconds": room.clock_initial_seconds,
        "increment_seconds": room.increment_seconds,
        "delay_seconds": room.delay_seconds,
        "host_display_name": room.host_display_name,
        "participants": participants,
        "last_activity_at": room.last_activity_at.isoformat() if room.last_activity_at else None,
    }
    if request is not None:
        payload["invite_url"] = absolute_invite_url(request, room)
    return payload


def room_accessible_to_user(room: Any, user: Any) -> bool:
    """Return whether a user may view a non-public room from authenticated dashboards."""

    if room.visibility == room.Visibility.PUBLIC:
        return True
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return room.host_id == user.id or room.participants.filter(user=user).exists()


def find_user_by_identifier(identifier: str):
    """Resolve a user by email or display name for future invite features."""

    UserModel = get_user_model()
    clean = identifier.strip()
    if "@" in clean:
        return UserModel.objects.filter(email__iexact=clean).first()
    return UserModel.objects.filter(display_name__iexact=clean).first()
