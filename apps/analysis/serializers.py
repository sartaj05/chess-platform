from __future__ import annotations

from rest_framework import serializers

from apps.analysis.models import GameAnalysisJob, MoveReview, OpeningBookLine, PositionAnalysis


class StartAnalysisSerializer(serializers.Serializer):
    analysis_type = serializers.ChoiceField(
        choices=GameAnalysisJob.AnalysisType.choices, default=GameAnalysisJob.AnalysisType.QUICK
    )
    depth = serializers.IntegerField(min_value=1, max_value=18, default=10)


class PositionAnalysisSerializer(serializers.Serializer):
    fen = serializers.CharField(max_length=180)
    depth = serializers.IntegerField(min_value=1, max_value=18, default=12)
    movetime_ms = serializers.IntegerField(min_value=100, max_value=10000, default=750)


class PositionAnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionAnalysis
        fields = [
            "id",
            "fen",
            "side_to_move",
            "depth",
            "bestmove_uci",
            "bestmove_san",
            "score_cp",
            "score_white_cp",
            "mate_score",
            "pv",
            "created_at",
        ]


class MoveReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoveReview
        fields = [
            "ply_number",
            "move_uci",
            "move_san",
            "classification",
            "before_score_white_cp",
            "after_score_white_cp",
            "bestmove_uci",
            "bestmove_san",
            "score_loss_cp",
            "comment",
        ]


class GameAnalysisJobSerializer(serializers.ModelSerializer):
    reviews = MoveReviewSerializer(source="move_reviews", many=True, read_only=True)

    class Meta:
        model = GameAnalysisJob
        fields = [
            "id",
            "game",
            "analysis_type",
            "status",
            "depth",
            "movetime_ms",
            "progress",
            "summary",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
            "reviews",
        ]


class OpeningBookLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpeningBookLine
        fields = [
            "eco",
            "name",
            "moves_uci",
            "moves_san",
            "fen_after",
            "frequency",
            "white_win_rate",
            "draw_rate",
            "black_win_rate",
        ]
