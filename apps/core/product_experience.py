from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.games.models import Game, GameMove
from apps.puzzles.models import PuzzleAttempt
from apps.tournaments.models import Tournament, TournamentEntry


def player_progress(user: User) -> dict:
    today = timezone.localdate()
    games = Game.objects.filter(Q(white_user=user) | Q(black_user=user))
    total_games = games.count()
    solved_puzzles = PuzzleAttempt.objects.filter(user=user, status=PuzzleAttempt.Status.SOLVED).count()
    achievements = [
        {"name": "First Move", "description": "Complete your first game", "icon": "♟", "current": total_games, "target": 1},
        {"name": "Tactician", "description": "Solve 5 chess puzzles", "icon": "◆", "current": solved_puzzles, "target": 5},
        {"name": "Bot Breaker", "description": "Unlock bot level 3", "icon": "♞", "current": user.bot_level, "target": 3},
        {"name": "Rated Regular", "description": "Complete 10 rated games", "icon": "↗", "current": user.rated_games, "target": 10},
    ]
    for achievement in achievements:
        achievement["unlocked"] = achievement["current"] >= achievement["target"]
        achievement["percentage"] = min(round(achievement["current"] * 100 / achievement["target"]), 100)
    goals = [
        {"name": "Play a game", "current": min(games.filter(created_at__date=today).count(), 1), "target": 1},
        {"name": "Solve a puzzle", "current": min(PuzzleAttempt.objects.filter(user=user, solved_at__date=today).count(), 1), "target": 1},
        {"name": "Make five moves", "current": min(GameMove.objects.filter(played_by_user=user, created_at__date=today).count(), 5), "target": 5},
    ]
    return {"achievements": achievements, "unlocked_count": sum(item["unlocked"] for item in achievements), "daily_goals": goals, "completed_goal_count": sum(item["current"] >= item["target"] for item in goals)}


def live_platform_activity() -> dict:
    active_query = Game.objects.filter(status=Game.Status.ACTIVE)
    recent_cutoff = timezone.now() - timedelta(minutes=15)
    winners = []
    for tournament in Tournament.objects.filter(is_public=True, status=Tournament.Status.COMPLETED).order_by("-updated_at")[:3]:
        winner = TournamentEntry.objects.filter(tournament=tournament).select_related("user").order_by("-score", "seed").first()
        if winner:
            winners.append({"tournament": tournament, "player": winner.user, "score": winner.score})
    return {"active_games": active_query[:4], "active_game_count": active_query.count(), "active_player_count": User.objects.filter(is_active=True, last_seen_at__gte=recent_cutoff).count(), "recent_winners": winners}
