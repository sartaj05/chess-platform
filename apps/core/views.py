import random

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.games.services import actor_from_request, create_same_pc_game, play_local_bot_reply
from apps.rooms.models import Room
from apps.rooms.services import create_room, join_room


class HomeView(View):
    template_name = "core/home.html"

    def get(self, request):
        return render(request, self.template_name)

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
            player_side = side if side != Room.ColorPreference.RANDOM else random.choice(["white", "black"])
            white_name, black_name = (name, "Bot") if player_side == "white" else ("Bot", name)
            game = create_same_pc_game(white_name=white_name, black_name=black_name, initial_minutes=10)
            game.metadata = {"mode": "local_ai", "player_color": player_side}
            game.save(update_fields=["metadata", "updated_at"])
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
                return redirect("core:home")
            return redirect(room.get_absolute_url())

        return redirect("core:home")


def health_check(request):
    return JsonResponse({"status": "ok", "service": "chess-platform"})


class OfflineModeInfoView(View):
    def get(self, request):
        return render(request, "core/offline_mode.html")
