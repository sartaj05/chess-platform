import random
import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.accounts.models import User, UserPreference
from apps.core.models import AchievementShare, NewsArticle, PlayerReward, ReferralInvite, Season
from apps.core.product_experience import live_platform_activity, player_progress
from apps.core.retention import (
    claim_mission,
    club_leaderboard,
    create_achievement_share,
    create_referral_invite,
    mission_dashboard,
    redeem_referral,
)
from apps.games.models import Game
from apps.games.services import actor_from_request, create_same_pc_game, play_local_bot_reply
from apps.rooms.models import Room
from apps.rooms.services import create_room, join_room
from apps.tournaments.models import Tournament, TournamentAnnouncement


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
            personality = request.POST.get("bot_personality", "balanced")
            if personality not in {"balanced", "aggressive", "positional", "defensive", "unpredictable"}:
                personality = "balanced"
            player_side = side if side != Room.ColorPreference.RANDOM else random.choice(["white", "black"])
            white_name, black_name = (name, "Bot") if player_side == "white" else ("Bot", name)
            game = create_same_pc_game(white_name=white_name, black_name=black_name, initial_minutes=10)
            game.metadata = {
                "mode": "local_ai", "player_color": player_side,
                "bot_level": selected_level, "bot_personality": personality,
            }
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


class GlobalSearchView(View):
    def get(self, request):
        query = request.GET.get("q", "").strip()[:100]
        players = User.objects.none()
        tournaments = Tournament.objects.none()
        games = Game.objects.none()
        if len(query) >= 2:
            players = User.objects.filter(
                Q(display_name__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query),
                is_active=True,
            ).exclude(preferences__profile_visibility=UserPreference.ProfileVisibility.PRIVATE)
            if not request.user.is_authenticated:
                players = players.exclude(preferences__profile_visibility=UserPreference.ProfileVisibility.PLAYERS)
            players = players[:20]
            tournaments = Tournament.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query), is_public=True
            ).select_related("organizer")[:20]
            game_filter = Q(white_display_name__icontains=query) | Q(black_display_name__icontains=query)
            try:
                game_filter |= Q(pk=uuid.UUID(query))
            except ValueError:
                pass
            visible_games = Q(allow_spectators=True)
            if request.user.is_authenticated:
                visible_games |= Q(white_user=request.user) | Q(black_user=request.user)
            games = Game.objects.filter(game_filter, visible_games).select_related("white_user", "black_user")[:20]
        return render(
            request,
            "core/search.html",
            {"query": query, "players": players, "tournaments": tournaments, "games": games},
        )


class CommunityHubView(LoginRequiredMixin, View):
    def get(self, request):
        rewards, _ = PlayerReward.objects.get_or_create(user=request.user)
        return render(request, "core/community_hub.html", {
            "missions": mission_dashboard(request.user), "rewards": rewards,
            "season": Season.objects.filter(is_active=True, starts_at__lte=timezone.now(),
                                             ends_at__gte=timezone.now()).first(),
            "club_leaderboard": club_leaderboard()[:20],
            "news": NewsArticle.objects.filter(is_published=True, published_at__lte=timezone.now())[:20],
            "tournament_announcements": TournamentAnnouncement.objects.filter(
                tournament__entries__user=request.user
            ).select_related("tournament", "author")[:20],
            "referral_codes": ReferralInvite.objects.filter(inviter=request.user),
            "achievements": player_progress(request.user)["achievements"],
        })

    def post(self, request):
        action = request.POST.get("action", "")
        try:
            if action == "claim_mission":
                claim_mission(request.user, int(request.POST.get("mission_id", 0)))
            elif action == "share_achievement":
                share = create_achievement_share(request.user, request.POST.get("achievement_key", ""))
                messages.success(request, f"Share link created: /achievements/{share.share_code}/")
            elif action == "create_referral":
                invite = create_referral_invite(request.user)
                messages.success(request, f"Invite code created: {invite.code}")
            elif action == "redeem_referral":
                redeem_referral(request.POST.get("code", ""), request.user)
                messages.success(request, "Referral applied. Your inviter earned 100 points.")
            else:
                raise ValueError("Unsupported community action.")
        except (ValueError, ReferralInvite.DoesNotExist) as exc:
            messages.error(request, str(exc))
        return redirect("core:community")


class AchievementShareView(View):
    def get(self, request, code):
        share = get_object_or_404(AchievementShare.objects.select_related("user"), share_code=code)
        return render(request, "core/achievement_share.html", {"share": share})
