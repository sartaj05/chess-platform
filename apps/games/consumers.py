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
        await self.send_json({"type": "connection.accepted", "game": payload})

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content: dict[str, Any], **kwargs) -> None:
        event_type = content.get("type")
        try:
            if event_type == "ping":
                await self.send_json({"type": "pong", "server_time": timezone.now().isoformat()})
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
        from apps.games.services import serialize_game

        game = (
            Game.objects.select_related("room", "white_user", "black_user")
            .prefetch_related("moves")
            .get(pk=self.game_id)
        )
        return serialize_game(game)

    @database_sync_to_async
    def _play_move(self, uci: str, client_lag_ms: int) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope, play_uci_move, serialize_game

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        play_uci_move(game=game, actor=actor, uci=uci, client_lag_ms=client_lag_ms)
        game = (
            Game.objects.select_related("room", "white_user", "black_user")
            .prefetch_related("moves")
            .get(pk=self.game_id)
        )
        return serialize_game(game)

    @database_sync_to_async
    def _resign(self) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope, resign_game, serialize_game

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        resign_game(game=game, actor=actor)
        game.refresh_from_db()
        return serialize_game(game)

    @database_sync_to_async
    def _abort(self) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import abort_game, actor_from_scope, serialize_game

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        abort_game(game=game, actor=actor)
        game.refresh_from_db()
        return serialize_game(game)

    @database_sync_to_async
    def _draw(self) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope, offer_or_accept_draw, serialize_game

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        offer_or_accept_draw(game=game, actor=actor)
        game.refresh_from_db()
        return serialize_game(game)

    @database_sync_to_async
    def _decline_draw(self) -> dict[str, Any]:
        from apps.games.models import Game
        from apps.games.services import actor_from_scope, decline_draw, serialize_game

        game = Game.objects.select_related("white_user", "black_user").prefetch_related("moves").get(pk=self.game_id)
        actor = actor_from_scope(self.scope, game)
        decline_draw(game=game, actor=actor)
        game.refresh_from_db()
        return serialize_game(game)
