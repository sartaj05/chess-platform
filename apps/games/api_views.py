from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action as drf_action
from rest_framework.response import Response

from apps.games.models import Game
from apps.games.serializers import (
    GameActionSerializer,
    GameSerializer,
    MoveInputSerializer,
    OfflineGameSyncSerializer,
)
from apps.games.services import (
    abort_game,
    actor_from_request,
    board_from_fen,
    color_from_board,
    decline_draw,
    offer_or_accept_draw,
    play_uci_move,
    resign_game,
    serialize_game,
)


class GameViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GameSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return (
            Game.objects.select_related("room", "white_user", "black_user")
            .prefetch_related("moves")
            .order_by("-created_at")
        )

    def retrieve(self, request, *args, **kwargs):
        game = self.get_object()
        return Response(serialize_game(game, request=request))

    @drf_action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny])
    def sync_offline(self, request):
        """Import a locally played game once, safely retryable by sync ID."""
        serializer = OfflineGameSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sync_id = str(data["sync_id"])
        existing = Game.objects.filter(metadata__offline_sync_id=sync_id).first()
        if existing:
            return Response({"game": serialize_game(existing, request=request), "created": False})
        board_from_fen(data["initial_fen"])
        current = board_from_fen(data["current_fen"])
        identity = actor_from_request(
            request, Game(white_display_name="Offline", black_display_name="Offline")
        ).identity
        metadata = {"source": "offline_sync", "offline_sync_id": sync_id, "mode": data["mode"], **data["metadata"]}
        game = Game.objects.create(
            status=Game.Status.FINISHED,
            termination=Game.Termination.IMPORTED,
            white_user=identity.user,
            white_guest_key=identity.guest_key,
            white_display_name=identity.display_name,
            black_display_name="Offline opponent",
            initial_fen=data["initial_fen"],
            current_fen=data["current_fen"],
            cached_pgn=data["pgn"],
            initial_pgn=data["pgn"],
            turn=color_from_board(current),
            fullmove_number=current.fullmove_number,
            ply_count=max(0, (current.fullmove_number - 1) * 2),
            result=Game.Result.ONGOING,
            metadata=metadata,
        )
        return Response(
            {"game": serialize_game(game, request=request), "created": True}, status=status.HTTP_201_CREATED
        )

    @drf_action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        game = self.get_object()

        serializer = MoveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        actor = actor_from_request(request, game)

        play_uci_move(
            game=game,
            actor=actor,
            uci=serializer.validated_data["uci"],
            client_lag_ms=serializer.validated_data.get("client_lag_ms", 0),
        )

        game.refresh_from_db()
        return Response(serialize_game(game, request=request), status=status.HTTP_200_OK)

    @drf_action(detail=True, methods=["post"])
    def game_action(self, request, pk=None):
        game = self.get_object()

        serializer = GameActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        actor = actor_from_request(request, game)
        action_name = serializer.validated_data["action"]

        if action_name == "resign":
            resign_game(game=game, actor=actor)
        elif action_name == "abort":
            abort_game(game=game, actor=actor)
        elif action_name == "draw":
            offer_or_accept_draw(game=game, actor=actor)
        elif action_name == "decline_draw":
            decline_draw(game=game, actor=actor)

        game.refresh_from_db()
        return Response(serialize_game(game, request=request))

    @drf_action(detail=True, methods=["get"])
    def fen(self, request, pk=None):
        game = get_object_or_404(Game, pk=pk)
        return Response({"fen": game.current_fen})

    @drf_action(detail=True, methods=["get"])
    def pgn(self, request, pk=None):
        game = get_object_or_404(Game, pk=pk)
        return Response({"pgn": game.cached_pgn})
