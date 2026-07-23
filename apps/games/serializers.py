from __future__ import annotations

from rest_framework import serializers

from apps.games.models import Game, GameMove


class GameMoveSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameMove
        fields = [
            "id",
            "ply_number",
            "move_number",
            "color",
            "uci",
            "san",
            "from_square",
            "to_square",
            "promotion",
            "white_time_ms",
            "black_time_ms",
            "played_by_display_name",
            "created_at",
        ]


class GameSerializer(serializers.ModelSerializer):
    moves = GameMoveSerializer(many=True, read_only=True)

    class Meta:
        model = Game
        fields = [
            "id",
            "room",
            "status",
            "rated",
            "white_display_name",
            "black_display_name",
            "current_fen",
            "initial_fen",
            "cached_pgn",
            "turn",
            "ply_count",
            "last_move_uci",
            "last_move_san",
            "clock_initial_ms",
            "increment_ms",
            "delay_ms",
            "white_time_ms",
            "black_time_ms",
            "result",
            "termination",
            "winner_color",
            "draw_offer_by",
            "moves",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MoveInputSerializer(serializers.Serializer):
    uci = serializers.CharField(max_length=8)
    client_lag_ms = serializers.IntegerField(min_value=0, required=False, default=0)


class GameActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["resign", "abort", "draw", "decline_draw"])


class OfflineGameSyncSerializer(serializers.Serializer):
    sync_id = serializers.UUIDField()
    initial_fen = serializers.CharField(max_length=150)
    current_fen = serializers.CharField(max_length=150)
    pgn = serializers.CharField(max_length=100000, allow_blank=True)
    mode = serializers.ChoiceField(choices=["same_device", "local_ai"])
    metadata = serializers.JSONField(required=False, default=dict)
