from __future__ import annotations

from django.contrib import admin

from apps.stockfish.models import StockfishEngineProfile, StockfishRun


@admin.register(StockfishEngineProfile)
class StockfishEngineProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "binary_path", "default_depth", "default_movetime_ms", "threads", "hash_mb", "skill_level", "is_active")
    list_filter = ("is_active", "skill_level")
    search_fields = ("name", "binary_path")


@admin.register(StockfishRun)
class StockfishRunAdmin(admin.ModelAdmin):
    list_display = ("created_at", "command_type", "status", "depth", "movetime_ms", "bestmove", "score_cp", "mate_score", "duration_ms")
    list_filter = ("status", "command_type", "created_at")
    search_fields = ("fen", "bestmove", "error_message")
    readonly_fields = ("created_at", "updated_at", "raw_info")
