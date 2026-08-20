from __future__ import annotations

from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone


class GameConsumer(AsyncJsonWebsocketConsumer):
    """Authoritative realtime gameplay consumer."""

    game_id: str
    group_name: str

    async def connect(self) -> None:
        self.game_id = str(self.scope["url_route"]["kwargs"]["game_id"])
        self.group_name = f"game_{self.game_id}"
        payload = await self._state()
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._presence(True)
        await self.send_json({"type": "connection.accepted", "game": payload})

    async def disconnect(self, close_code: int) -> None:
        await self._presence(False)
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content: dict[str, Any], **kwargs) -> None:
        event_type = content.get("type")
        try:
            if event_type == "ping":
                await self.send_json({"type": "pong", "server_time": timezone.now().isoformat()})
                return
            if event_type == "game.sync":
                await self.send_json({"type": "game.synced", "game": await self._state()})
                return
            if event_type == "game.move":
                payload = await self._play_move(str(content.get("uci", "")), int(content.get("client_lag_ms", 0) or 0))
                await self.channel_layer.group_send(
                    self.group_name, {"type": "broadcast_game", "event": "move.played", "game": payload}
                )
                return
            if event_type == "game.resign":
                payload = await self._resign()
                await self.channel_layer.group_send(
                    self.group_name, {"type": "broadcast_game", "event": "game.resigned", "game": payload}
                )
                return
            if event_type == "game.abort":
                payload = await self._abort()
                await self.channel_layer.group_send(
                    self.group_name, {"type": "broadcast_game", "event": "game.aborted", "game": payload}
                )
                return
            if event_type == "game.draw":
                payload = await self._draw()
                await self.channel_layer.group_send(
                    self.group_name, {"type": "broadcast_game", "event": "draw.updated", "game": payload}
                )
                return
            if event_type == "game.decline_draw":
                payload = await self._decline_draw()
                await self.channel_layer.group_send(
                    self.group_name, {"type": "broadcast_game", "event": "draw.declined", "game": payload}
                )
                return
            if event_type == "game.rematch":
                payload = await self._rematch()
                await self.channel_layer.group_send(
                    self.group_name, {"type": "broadcast_game", "event": "rematch.updated", "game": payload}
                )
                return
            if event_type == "game.claim_draw":
                payload = await self._claim_draw(str(content.get("rule", "")))
                await self.channel_layer.group_send(
                    self.group_name, {"type": "broadcast_game", "event": "draw.claimed", "game": payload}
                )
                return
            if event_type in {"game.takeback", "game.decline_takeback"}:
                payload = await self._takeback(event_type == "game.decline_takeback")
                await self.channel_layer.group_send(
                    self.group_name, {"type": "broadcast_game", "event": "takeback.updated", "game": payload}
                )
                return
            if event_type == "game.chat":
                payload = await self._chat(str(content.get("body", "")), str(content.get("audience", "all")))
                await self.channel_layer.group_send(self.group_name, {"type": "broadcast_chat", "message": payload})
                return
            if event_type in {"game.chat.report", "game.chat.remove"}:
                payload = await self._moderate_chat(str(content.get("message_id", "")), event_type.endswith("remove"))
                await self.channel_layer.group_send(
                    self.group_name, {"type": "broadcast_chat_moderated", "message": payload}
                )
                return
        except PermissionDenied as exc:
            await self.send_json({"type": "error", "message": str(exc)})
            return
        except ValidationError as exc:
            await self.send_json({"type": "error", "message": "; ".join(exc.messages)})
            return
        except Exception:
            await self.send_json({"type": "error", "message": "Unable to process the game event."})
            return
        await self.send_json({"type": "error", "message": "Unsupported game event."})

    async def broadcast_game(self, event: dict[str, Any]) -> None:
        await self.send_json({"type": "game.state", "event": event.get("event"), "game": event["game"]})

    async def broadcast_chat(self, event):
        audience = event["message"].get("audience", "all")
        role = await self._viewer_role()
        if audience != "all" and audience != f"{role}s":
            return
        await self.send_json({"type": "game.chat", "message": event["message"]})

    async def broadcast_chat_moderated(self, event):
        await self.send_json({"type": "game.chat.moderated", "message": event["message"]})

    def _serialized_for_viewer(self, game: Any) -> dict[str, Any]:
        from apps.games.services import actor_from_scope, serialize_game

        actor = actor_from_scope(self.scope, game)
        payload = serialize_game(game)
        payload["viewer"] = {
            "color": actor.color,
            "name": actor.display_name,
            "can_move": actor.color == game.turn,
        }
        return payload

    @database_sync_to_async
    def _get_game(self):
        from apps.games.models import Game

        return (
            Game.objects.select_related("room", "white_user", "black_user")
            .prefetch_related("moves")
            .get(pk=self.game_id)
        )

    @database_sync_to_async
    def _state(self) -> dict[str, Any]:
        from apps.games.models import Game

        game = (
            Game.objects.select_related("room", "white_user", "black_user")
            .prefetch_related("moves")
            .get(pk=self.game_id)
        )
        return self._serialized_for_viewer(game)

    @database_sync_to_async
    def _presence(self, connected: bool) -> None:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope

        game = Game.objects.select_related("white_user", "black_user").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        if actor.color not in {"white", "black"}:
            return
        field = f"{actor.color}_disconnected_at"
        setattr(game, field, None if connected else timezone.now())
        game.save(update_fields=[field, "updated_at"])

    @database_sync_to_async
    def _play_move(self, uci: str, client_lag_ms: int) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope, play_local_bot_reply, play_uci_move

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        play_uci_move(game=game, actor=actor, uci=uci, client_lag_ms=client_lag_ms)
        game.refresh_from_db()
        play_local_bot_reply(game=game, actor=actor_from_scope(self.scope, game))
        game = (
            Game.objects.select_related("room", "white_user", "black_user")
            .prefetch_related("moves")
            .get(pk=self.game_id)
        )
        return self._serialized_for_viewer(game)

    @database_sync_to_async
    def _resign(self) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope, resign_game

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        resign_game(game=game, actor=actor)
        game.refresh_from_db()
        return self._serialized_for_viewer(game)

    @database_sync_to_async
    def _abort(self) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import abort_game, actor_from_scope

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        abort_game(game=game, actor=actor)
        game.refresh_from_db()
        return self._serialized_for_viewer(game)

    @database_sync_to_async
    def _draw(self) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope, offer_or_accept_draw

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        offer_or_accept_draw(game=game, actor=actor)
        game.refresh_from_db()
        return self._serialized_for_viewer(game)

    @database_sync_to_async
    def _decline_draw(self) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope, decline_draw

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        decline_draw(game=game, actor=actor)
        game.refresh_from_db()
        return self._serialized_for_viewer(game)

    @database_sync_to_async
    def _rematch(self) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope, request_rematch

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        request_rematch(game=game, actor=actor_from_scope(self.scope, game))
        game.refresh_from_db()
        return self._serialized_for_viewer(game)

    @database_sync_to_async
    def _claim_draw(self, rule: str) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope, claim_rule_draw

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        claim_rule_draw(game=game, actor=actor_from_scope(self.scope, game), rule=rule)
        game.refresh_from_db()
        return self._serialized_for_viewer(game)

    @database_sync_to_async
    def _takeback(self, decline: bool) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope, decline_takeback, offer_or_accept_takeback

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        decline_takeback(game=game, actor=actor) if decline else offer_or_accept_takeback(game=game, actor=actor)
        game.refresh_from_db()
        return self._serialized_for_viewer(game)

    @database_sync_to_async
    def _chat(self, body: str, audience: str) -> dict[str, Any]:
        from apps.games.models import Game, GameChatMessage
        from apps.games.services import actor_from_scope

        game = Game.objects.get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        clean = " ".join(body.strip().split())[:500]
        if not clean:
            raise ValidationError("Message cannot be empty.")
        role = "player" if actor.color in {"white", "black"} else "spectator"
        if audience not in GameChatMessage.Audience.values:
            audience = GameChatMessage.Audience.ALL
        message = GameChatMessage.objects.create(
            game=game,
            sender=actor.identity.user,
            sender_name=actor.display_name,
            sender_role=role,
            body=clean,
            audience=audience,
        )
        return {
            "id": str(message.pk),
            "sender": message.sender_name,
            "role": role,
            "body": clean,
            "audience": audience,
            "created_at": message.created_at.isoformat(),
            "removed": False,
        }

    @database_sync_to_async
    def _viewer_role(self) -> str:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope

        actor = actor_from_scope(self.scope, Game.objects.get(pk=self.game_id))
        return "player" if actor.color in {"white", "black"} else "spectator"

    @database_sync_to_async
    def _moderate_chat(self, message_id: str, remove: bool) -> dict[str, Any]:
        from apps.games.models import GameChatMessage

        message = GameChatMessage.objects.select_related("sender").get(pk=message_id, game_id=self.game_id)
        user = self.scope.get("user")
        if remove:
            if not getattr(user, "is_staff", False):
                raise PermissionDenied("Only moderators can remove messages.")
            message.is_removed = True
        else:
            message.reports += 1
        message.save(update_fields=["is_removed", "reports", "updated_at"])
        return {"id": str(message.pk), "removed": message.is_removed, "reports": message.reports}
