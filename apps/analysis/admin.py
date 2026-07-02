from __future__ import annotations

from django.contrib import admin

from apps.analysis.models import GameAnalysisJob, MoveReview, OpeningBookLine, OpeningExplorerQuery, PositionAnalysis


@admin.register(GameAnalysisJob)
class GameAnalysisJobAdmin(admin.ModelAdmin):
    list_display = ("created_at", "game", "analysis_type", "status", "depth", "progress", "requested_by")
    list_filter = ("status", "analysis_type", "created_at")
    search_fields = ("game__white_display_name", "game__black_display_name", "error_message")
    readonly_fields = ("summary", "created_at", "updated_at")


@admin.register(PositionAnalysis)
class PositionAnalysisAdmin(admin.ModelAdmin):
    list_display = ("created_at", "game", "side_to_move", "depth", "bestmove_uci", "score_white_cp", "mate_score")
    list_filter = ("side_to_move", "created_at")
    search_fields = ("fen", "bestmove_uci")
    readonly_fields = ("raw_engine", "pv")


@admin.register(MoveReview)
class MoveReviewAdmin(admin.ModelAdmin):
    list_display = ("game", "ply_number", "move_san", "classification", "score_loss_cp", "bestmove_san")
    list_filter = ("classification", "created_at")
    search_fields = ("move_san", "move_uci", "bestmove_san")


@admin.register(OpeningBookLine)
class OpeningBookLineAdmin(admin.ModelAdmin):
    list_display = ("eco", "name", "moves_san", "frequency", "is_active")
    list_filter = ("eco", "is_active")
    search_fields = ("eco", "name", "moves_san")


@admin.register(OpeningExplorerQuery)
class OpeningExplorerQueryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "moves_uci", "result_count", "ip_address")
    list_filter = ("created_at",)
