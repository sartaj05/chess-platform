from __future__ import annotations

from django.contrib import admin

from apps.games.models import Game, GameEvent, GameMove


class GameMoveInline(admin.TabularInline):
    model = GameMove
    extra = 0
    readonly_fields = (
        "ply_number",
        "move_number",
        "color",
        "uci",
        "san",
        "white_time_ms",
        "black_time_ms",
        "created_at",
    )
    can_delete = False


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("id", "white_display_name", "black_display_name", "status", "result", "turn", "rated", "created_at")
    list_filter = ("status", "result", "termination", "rated", "turn")
    search_fields = ("white_display_name", "black_display_name", "current_fen", "room__code")
    readonly_fields = ("created_at", "updated_at", "cached_pgn")
    inlines = [GameMoveInline]
    fieldsets = (
        (
            "Players",
            {
                "fields": (
                    "room",
                    "white_user",
                    "black_user",
                    "white_display_name",
                    "black_display_name",
                    "rated",
                    "allow_spectators",
                )
            },
        ),
        (
            "State",
            {
                "fields": (
                    "status",
                    "result",
                    "termination",
                    "winner_color",
                    "turn",
                    "ply_count",
                    "fullmove_number",
                    "last_move_uci",
                    "last_move_san",
                )
            },
        ),
        ("Board", {"fields": ("initial_fen", "current_fen", "cached_pgn")}),
        (
            "Clock",
            {
                "fields": (
                    "clock_initial_ms",
                    "increment_ms",
                    "delay_ms",
                    "white_time_ms",
                    "black_time_ms",
                    "clock_started_at",
                    "last_move_at",
                )
            },
        ),
        ("Dates", {"fields": ("started_at", "ended_at", "created_at", "updated_at")}),
    )


@admin.register(GameMove)
class GameMoveAdmin(admin.ModelAdmin):
    list_display = ("game", "ply_number", "move_number", "color", "san", "uci", "created_at")
    list_filter = ("color",)
    search_fields = ("game__id", "uci", "san", "played_by_display_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(GameEvent)
class GameEventAdmin(admin.ModelAdmin):
    list_display = ("game", "event_type", "actor_display_name", "actor_color", "created_at")
    list_filter = ("event_type", "actor_color")
    search_fields = ("game__id", "actor_display_name")
    readonly_fields = ("created_at", "updated_at")
