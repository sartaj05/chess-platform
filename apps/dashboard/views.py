from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView, TemplateView

from apps.accounts.models import User
from apps.chat.models import Message
from apps.friends.models import Friendship
from apps.games.models import Game
from apps.puzzles.models import PuzzleAttempt
from apps.tournaments.models import Tournament, TournamentEntry


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        games = Game.objects.filter(Q(white_user=user) | Q(black_user=user))
        finished_games = games.filter(status=Game.Status.FINISHED)
        wins = finished_games.filter(
            Q(white_user=user, result=Game.Result.WHITE_WIN) | Q(black_user=user, result=Game.Result.BLACK_WIN)
        ).count()
        losses = finished_games.filter(
            Q(white_user=user, result=Game.Result.BLACK_WIN) | Q(black_user=user, result=Game.Result.WHITE_WIN)
        ).count()
        draws = finished_games.filter(result=Game.Result.DRAW).count()
        finished_count = finished_games.count()

        friend_count = Friendship.objects.filter(
            Q(requester=user) | Q(addressee=user),
            status=Friendship.Status.ACCEPTED,
        ).count()
        puzzle_attempts = PuzzleAttempt.objects.filter(user=user)
        unread_messages = Message.objects.filter(
            Q(conversation__first_user=user) | Q(conversation__second_user=user),
            read_at__isnull=True,
        ).exclude(sender=user)
        tournament_entries = TournamentEntry.objects.filter(user=user).select_related("tournament")

        context.update(
            game_stats={
                "total": games.count(),
                "active": games.filter(status=Game.Status.ACTIVE).count(),
                "wins": wins,
                "losses": losses,
                "draws": draws,
            },
            friend_count=friend_count,
            puzzle_stats={
                "attempted": puzzle_attempts.count(),
                "solved": puzzle_attempts.filter(status=PuzzleAttempt.Status.SOLVED).count(),
            },
            unread_message_count=unread_messages.count(),
            finished_game_count=finished_count,
            win_percentage=round(wins * 100 / finished_count) if finished_count else 0,
            result_loss_end=round((wins + losses) * 100 / finished_count) if finished_count else 0,
            rating_progress={
                "bullet": min(round(user.bullet_rating / 20), 100),
                "blitz": min(round(user.blitz_rating / 20), 100),
                "rapid": min(round(user.rapid_rating / 20), 100),
            },
            puzzle_percentage=round(
                puzzle_attempts.filter(status=PuzzleAttempt.Status.SOLVED).count() * 100 / puzzle_attempts.count()
            )
            if puzzle_attempts.exists()
            else 0,
            recent_games=games.select_related("white_user", "black_user")[:5],
            upcoming_tournaments=tournament_entries.filter(
                tournament__status__in=[Tournament.Status.REGISTRATION, Tournament.Status.ACTIVE]
            )[:5],
        )
        return context


class LeaderboardView(ListView):
    model = User
    template_name = "dashboard/leaderboard.html"
    context_object_name = "players"
    paginate_by = 50

    def get_queryset(self):
        category = self.request.GET.get("category", "blitz")
        if category not in {"bullet", "blitz", "rapid"}:
            category = "blitz"
        self.category = category
        return User.objects.filter(is_active=True).order_by(f"-{category}_rating", f"-{category}_games", "display_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
        return context
