from __future__ import annotations

import chess
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response

from apps.api.throttles import AnalysisAnonRateThrottle, AnalysisUserRateThrottle
from apps.stockfish.engine import StockfishUnavailableError
from apps.stockfish.services import analyse_fen_with_stockfish


class MobileBestMoveSerializer(serializers.Serializer):
    fen = serializers.CharField(max_length=150)
    level = serializers.IntegerField(min_value=1, max_value=10, default=1)

    def validate_fen(self, value: str) -> str:
        try:
            chess.Board(value)
        except ValueError as exc:
            raise serializers.ValidationError("Enter a valid chess position.") from exc
        return value


class MobileBestMoveAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnalysisAnonRateThrottle, AnalysisUserRateThrottle]

    def post(self, request):
        serializer = MobileBestMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        level = serializer.validated_data["level"]
        try:
            result = analyse_fen_with_stockfish(
                fen=serializer.validated_data["fen"],
                skill_level=min(20, level * 2),
                depth=min(16, 6 + level),
                movetime_ms=100 + level * 75,
                command_type="mobile_bot_move",
            )
        except StockfishUnavailableError:
            return Response(
                {"detail": "Stockfish is not available on the server."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "bestmove": result.bestmove,
                "depth": result.depth,
                "duration_ms": result.duration_ms,
                "engine": "Stockfish",
            }
        )
