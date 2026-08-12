from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.rooms.services import GUEST_NAME_SESSION_KEY, GUEST_SESSION_KEY, identity_from_scope


class RoomConsumer(AsyncJsonWebsocketConsumer):
    """Realtime lobby consumer for room presence, chat, and ready state."""

    room_code: str
    group_name: str
    participant_id: str | None = None

    async def connect(self) -> None:
        self.room_code = self.scope["url_route"]["kwargs"]["code"].upper()
        self.group_name = f"room_{self.room_code.lower()}"
        try:
            payload = await self._connect_participant()
        except (ValidationError, PermissionDenied):
            await self.close(code=4403)
            return
        except Exception:
            await self.close(code=4404)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json(
            {"type": "connection.accepted", "room": payload["room"], "participant": payload["participant"]}
        )
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "broadcast_state", "event": "participant.connected", "room": payload["room"]},
        )

    async def disconnect(self, close_code: int) -> None:
        if getattr(self, "group_name", None):
            room_payload = await self._disconnect_participant()
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            if room_payload is not None:
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "broadcast_state", "event": "participant.disconnected", "room": room_payload},
                )

    async def receive_json(self, content: dict[str, Any], **kwargs) -> None:
        event_type = content.get("type")
        if event_type == "ping":
            await self.send_json({"type": "pong", "server_time": timezone.now().isoformat()})
            return
        if event_type == "room.chat":
            message = str(content.get("message", "")).strip()
            if not message:
                await self.send_json({"type": "error", "message": "Message cannot be empty."})
                return
            if len(message) > 500:
                await self.send_json({"type": "error", "message": "Message is too long."})
                return
            chat_payload = await self._save_chat_message(message)
            await self.channel_layer.group_send(self.group_name, {"type": "broadcast_chat", "chat": chat_payload})
            return
        if event_type == "room.ready":
            ready = bool(content.get("ready", True))
            room_payload = await self._set_ready(ready)
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "broadcast_state", "event": "participant.ready", "room": room_payload},
            )
            return
        if event_type == "room.leave":
            room_payload = await self._leave_participant()
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "broadcast_state", "event": "participant.left", "room": room_payload},
            )
            await self.close(code=1000)
            return
        await self.send_json({"type": "error", "message": "Unsupported room event."})

    async def broadcast_state(self, event: dict[str, Any]) -> None:
        await self.send_json({"type": "room.state", "event": event.get("event"), "room": event["room"]})

    async def broadcast_chat(self, event: dict[str, Any]) -> None:
        await self.send_json({"type": "room.chat", "chat": event["chat"]})

    async def broadcast_game_started(self, event: dict[str, Any]) -> None:
        await self.send_json({"type": "game.started", "game": event["game"]})

    @database_sync_to_async
    def _connect_participant(self) -> dict[str, Any]:
        from apps.rooms.models import Room
        from apps.rooms.services import join_room, serialize_participant, serialize_room

        room = Room.objects.prefetch_related("participants").get(code=self.room_code)
        identity = identity_from_scope(self.scope)
        session = self.scope.get("session")
        if session is None or not hasattr(session, "modified"):

            class FallbackSession(dict):
                modified = False

            session = FallbackSession(
                {GUEST_SESSION_KEY: identity.guest_key, GUEST_NAME_SESSION_KEY: identity.display_name}
            )
        scope_request = SimpleNamespace(user=identity.user, session=session)

        participant = join_room(request=scope_request, room=room, display_name=identity.display_name)
        participant.mark_connected()
        self.participant_id = str(participant.id)
        room.refresh_from_db()
        return {"room": serialize_room(room), "participant": serialize_participant(participant)}

    @database_sync_to_async
    def _disconnect_participant(self) -> dict[str, Any] | None:
        from apps.rooms.models import RoomParticipant
        from apps.rooms.services import serialize_room

        if not self.participant_id:
            return None
        participant = RoomParticipant.objects.select_related("room").filter(id=self.participant_id).first()
        if participant is None:
            return None
        participant.mark_disconnected()
        participant.room.touch()
        return serialize_room(participant.room)

    @database_sync_to_async
    def _save_chat_message(self, message: str) -> dict[str, Any]:
        from apps.rooms.models import RoomEvent, RoomParticipant

        participant = RoomParticipant.objects.select_related("room", "user").get(id=self.participant_id)
        event = RoomEvent.objects.create(
            room=participant.room,
            event_type=RoomEvent.EventType.CHAT_MESSAGE,
            actor_user=participant.user,
            actor_guest_key=participant.guest_key,
            actor_display_name=participant.display_name,
            payload={"message": message},
        )
        participant.room.touch()
        return {
            "id": str(event.id),
            "message": message,
            "actor": participant.display_name,
            "created_at": event.created_at.isoformat(),
        }

    @database_sync_to_async
    def _set_ready(self, ready: bool) -> dict[str, Any]:
        from apps.rooms.models import RoomEvent, RoomParticipant
        from apps.rooms.services import serialize_room

        participant = RoomParticipant.objects.select_related("room", "user").get(id=self.participant_id)
        participant.mark_ready(ready)
        RoomEvent.objects.create(
            room=participant.room,
            event_type=RoomEvent.EventType.PARTICIPANT_READY,
            actor_user=participant.user,
            actor_guest_key=participant.guest_key,
            actor_display_name=participant.display_name,
            payload={"ready": ready},
        )
        participant.room.touch()
        return serialize_room(participant.room)

    @database_sync_to_async
    def _leave_participant(self) -> dict[str, Any]:
        from apps.rooms.models import RoomEvent, RoomParticipant
        from apps.rooms.services import serialize_room

        participant = RoomParticipant.objects.select_related("room", "user").get(id=self.participant_id)
        participant.leave()
        RoomEvent.objects.create(
            room=participant.room,
            event_type=RoomEvent.EventType.PARTICIPANT_LEFT,
            actor_user=participant.user,
            actor_guest_key=participant.guest_key,
            actor_display_name=participant.display_name,
            payload={"source": "websocket"},
        )
        participant.room.touch()
        return serialize_room(participant.room)
