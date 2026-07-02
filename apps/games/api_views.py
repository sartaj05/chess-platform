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
)
from apps.games.services import (
    actor_from_request,
    abort_game,
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