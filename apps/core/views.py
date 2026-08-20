import random

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.product_experience import live_platform_activity, player_progress
from apps.games.services import actor_from_request, create_same_pc_game, play_local_bot_reply
from apps.rooms.models import Room
from apps.rooms.services import create_room, join_room


class HomeView(View):
    template_name = "core/home.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        return self.render_page(request, show_marketing=True)

    def render_page(self, request, *, show_marketing):
        bot_level = request.user.bot_level if request.user.is_authenticated else 1
        context = {
            "bot_level": bot_level,
            "bot_levels": range(1, bot_level + 1),
            "show_marketing": show_marketing,
            **live_platform_activity(),
        }
        if request.user.is_authenticated:
            context.update(player_progress(request.user))
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get("action", "")
        name = request.POST.get("display_name", "").strip()[:80] or (
            request.user.display_name if request.user.is_authenticated else "Player"
        )
        side = request.POST.get("side", Room.ColorPreference.RANDOM)
        if side not in Room.ColorPreference.values:
            side = Room.ColorPreference.RANDOM

        if action == "same_pc":
            white_name, black_name = (name, "Friend")
            if side == Room.ColorPreference.BLACK:
                white_name, black_name = "Friend", name
            game = create_same_pc_game(white_name=white_name, black_name=black_name, initial_minutes=10)
            return redirect(game.get_absolute_url())

        if action == "bot":
            unlocked_level = request.user.bot_level if request.user.is_authenticated else 1
            try:
                selected_level = int(request.POST.get("bot_level", unlocked_level))
            except (TypeError, ValueError):
                selected_level = unlocked_level
            selected_level = max(1, min(selected_level, unlocked_level, 10))
            player_side = side if side != Room.ColorPreference.RANDOM else random.choice(["white", "black"])
            white_name, black_name = (name, "Bot") if player_side == "white" else ("Bot", name)
            game = create_same_pc_game(white_name=white_name, black_name=black_name, initial_minutes=10)
            game.metadata = {"mode": "local_ai", "player_color": player_side, "bot_level": selected_level}
            if request.user.is_authenticated:
                if player_side == "white":
                    game.white_user = request.user
                else:
                    game.black_user = request.user
            game.save(update_fields=["metadata", "white_user", "black_user", "updated_at"])
            if player_side == "black":
                play_local_bot_reply(game=game, actor=actor_from_request(request, game))
            return redirect(game.get_absolute_url())

        if action == "create_room":
            room = create_room(
                request=request,
                cleaned_data={
                    "name": f"{name}'s game",
                    "host_display_name": name,
                    "mode": Room.Mode.ONLINE,
                    "visibility": Room.Visibility.PRIVATE,
                    "clock_initial_minutes": 10,
                    "increment_seconds": 0,
                    "delay_seconds": 0,
                    "color_preference": side,
                    "rated": False,
                    "allow_guests": True,
                    "spectator_enabled": False,
                },
            )
            messages.success(request, f"Share code {room.code} with your friend.")
            return redirect(room.get_absolute_url())

        if action == "join_room":
            room = get_object_or_404(Room, code=request.POST.get("room_code", "").strip().upper())
            try:
                join_room(request=request, room=room, display_name=name)
            except (ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
                return redirect("core:play" if request.user.is_authenticated else "core:home")
            return redirect(room.get_absolute_url())

        return redirect("core:play" if request.user.is_authenticated else "core:home")


class PlayView(LoginRequiredMixin, HomeView):
    """Focused play workspace for signed-in players."""

    def get(self, request):
        return self.render_page(request, show_marketing=False)


def health_check(request):
    import time

    from django.core.cache import cache
    from django.db import connection
    checks = {"database": False, "cache": False}
    timings = {}
    started = time.perf_counter()
    try:
        check_started = time.perf_counter()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"] = cursor.fetchone()[0] == 1
        timings["database_ms"] = round((time.perf_counter() - check_started) * 1000, 2)
    except Exception:
        timings["database_ms"] = None
        pass
    try:
        check_started = time.perf_counter()
        cache.set("health-check", "ok", 10)
        checks["cache"] = cache.get("health-check") == "ok"
        timings["cache_ms"] = round((time.perf_counter() - check_started) * 1000, 2)
    except Exception:
        timings["cache_ms"] = None
        pass
    healthy = all(checks.values())
    timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return JsonResponse(
        {
            "status": "ok" if healthy else "degraded",
            "service": "chess-platform",
            "checks": checks,
            "timings": timings,
        },
        status=200 if healthy else 503,
    )


class OfflineModeInfoView(View):
    def get(self, request):
        return render(request, "core/offline_mode.html")
