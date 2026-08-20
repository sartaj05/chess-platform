from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.product_experience import player_progress
from apps.games.models import Game
from apps.tournaments.models import Tournament, TournamentEntry

from .models import User
from .serializers import MobileEmailVerificationSerializer, MobileRegistrationSerializer, UserSerializer
from .tasks import send_email_verification


class LeaderboardAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        category = request.query_params.get("category", "blitz")
        if category not in {"bullet", "blitz", "rapid"}:
            category = "blitz"
        players = User.objects.filter(is_active=True).order_by(f"-{category}_rating", f"-{category}_games")[:100]
        return Response({"category": category, "results": UserSerializer(players, many=True, context={"request": request}).data})


class PublicProfileAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        user = User.objects.filter(pk=pk, is_active=True).first()
        if user is None:
            return Response({"detail": "Player not found."}, status=404)
        return Response(UserSerializer(user, context={"request": request}).data)


class MobileExperienceAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        payload = player_progress(request.user)
        public_active_games = Game.objects.filter(
            status=Game.Status.ACTIVE,
            allow_spectators=True,
            room__visibility="public",
        )
        active_games = (
            public_active_games
            .select_related("room")
            .order_by("-last_move_at", "-created_at")[:6]
        )
        resume_games = (
            Game.objects.filter(
                Q(white_user=request.user) | Q(black_user=request.user),
                status__in=[Game.Status.CREATED, Game.Status.ACTIVE, Game.Status.PAUSED],
                room__isnull=False,
            )
            .select_related("room")
            .order_by("-updated_at")[:3]
        )
        recent_winners = []
        tournaments = Tournament.objects.filter(
            is_public=True, status=Tournament.Status.COMPLETED
        ).order_by("-updated_at")[:3]
        for tournament in tournaments:
            winner = (
                TournamentEntry.objects.filter(tournament=tournament)
                .select_related("user")
                .order_by("-score", "seed")
                .first()
            )
            if winner:
                recent_winners.append(
                    {
                        "tournament": tournament.name,
                        "player": winner.user.display_name,
                        "player_id": str(winner.user_id),
                        "score": float(winner.score),
                    }
                )

        def game_row(game):
            return {
                "id": str(game.pk),
                "room_code": game.room.code,
                "white": game.white_display_name,
                "black": game.black_display_name,
                "turn": game.turn,
                "ply_count": game.ply_count,
                "time_control": game.room.time_control_label,
            }

        active_user_ids = set(
            public_active_games.values_list("white_user_id", flat=True)
        ) | set(public_active_games.values_list("black_user_id", flat=True))
        active_user_ids.discard(None)
        payload["live_activity"] = {
            "active_game_count": public_active_games.count(),
            "active_player_count": len(active_user_ids),
            "active_games": [game_row(game) for game in active_games],
            "resume_games": [game_row(game) for game in resume_games],
            "recent_winners": recent_winners,
        }
        return Response(payload)


class PlayerComparisonAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        other = User.objects.filter(pk=pk, is_active=True).first()
        if other is None:
            return Response({"detail": "Player not found."}, status=404)

        def stats(player):
            games = Game.objects.filter(
                Q(white_user=player) | Q(black_user=player),
                status=Game.Status.FINISHED,
            )
            total = games.count()
            wins = games.filter(
                Q(white_user=player, result=Game.Result.WHITE_WIN)
                | Q(black_user=player, result=Game.Result.BLACK_WIN)
            ).count()
            return {
                "profile": UserSerializer(player, context={"request": request}).data,
                "games": total,
                "wins": wins,
                "draws": games.filter(result=Game.Result.DRAW).count(),
                "win_rate": round(wins * 100 / total) if total else 0,
            }

        return Response({"first": stats(request.user), "second": stats(other)})


class PuzzleListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.puzzles.models import Puzzle, PuzzleCourse
        rows = Puzzle.objects.filter(is_published=True).order_by("rating")[:100]
        daily = Puzzle.objects.filter(is_published=True).order_by("id")[timezone.localdate().toordinal() % max(Puzzle.objects.filter(is_published=True).count(), 1)] if rows else None
        leaders = User.objects.filter(is_active=True).order_by("-puzzle_rating", "display_name")[:20]
        courses = PuzzleCourse.objects.filter(is_published=True).prefetch_related("items__puzzle")
        return Response({"daily_id": daily.pk if daily else None, "puzzle_rating": request.user.puzzle_rating, "streak": request.user.puzzle_streak, "best_streak": request.user.puzzle_best_streak, "leaderboard": [{"name":u.display_name,"rating":u.puzzle_rating,"streak":u.puzzle_streak} for u in leaders], "courses":[{"id": course.pk,"title":course.title,"description":course.description,"theme":course.theme,"difficulty":course.difficulty,"puzzle_ids":[item.puzzle_id for item in course.items.all()]} for course in courses], "results":[{"id": row.pk, "title": row.title, "fen": row.initial_fen, "rating": row.rating, "difficulty": row.difficulty, "themes": row.themes, "course_ids": list(row.courses.values_list("id", flat=True))} for row in rows]})


class PuzzlePlayAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from apps.puzzles.models import Puzzle
        from apps.puzzles.services import get_attempt, submit_move
        puzzle = Puzzle.objects.filter(pk=pk, is_published=True).first()
        if puzzle is None:
            return Response({"detail": "Puzzle not found."}, status=404)
        attempt = get_attempt(puzzle=puzzle, user=request.user)
        correct, reply = submit_move(attempt=attempt, move_text=str(request.data.get("move", "")))
        attempt.refresh_from_db()
        solved = attempt.status == attempt.Status.SOLVED
        return Response({"correct": correct, "reply": reply, "fen": attempt.current_fen, "status": attempt.status, "mistakes": attempt.mistakes, "rating_change": attempt.rating_change, "puzzle_rating": request.user.puzzle_rating, "streak": request.user.puzzle_streak, "explanation": puzzle.explanation if solved else "", "solution_moves": puzzle.solution_moves if solved else []})


class MeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    @extend_schema(request=UserSerializer, responses=UserSerializer)
    def patch(self, request):
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MobileDataExportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        games = Game.objects.filter(Q(white_user=user) | Q(black_user=user)).order_by("created_at")
        preference = getattr(user, "preferences", None)
        return Response({
            "exported_at": timezone.now(),
            "account": UserSerializer(user, context={"request": request}).data,
            "preferences": model_to_dict(preference) if preference else {},
            "games": [{
                "id": str(game.pk), "white": game.white_display_name,
                "black": game.black_display_name, "result": game.result,
                "status": game.status, "fen": game.current_fen,
                "pgn": game.cached_pgn, "created_at": game.created_at,
            } for game in games],
        })


class MobileDeleteAccountAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if str(request.data.get("confirmation", "")) != "DELETE":
            return Response({"confirmation": ["Type DELETE to confirm."]}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(str(request.data.get("password", ""))):
            return Response({"password": ["Incorrect password."]}, status=status.HTTP_400_BAD_REQUEST)
        request._request._account_deleted = True
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MobileRegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MobileRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_email_verification(
            str(user.id),
            request.get_host(),
            "https" if request.is_secure() else "http",
            request.META.get("REMOTE_ADDR"),
            request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response(
            {"detail": "Account created. Enter the verification code sent to your email."},
            status=status.HTTP_201_CREATED,
        )


class MobileVerifyEmailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = MobileEmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.is_active = True
        user.is_email_verified = True
        user.save(update_fields=["is_active", "is_email_verified"])
        return Response({"detail": "Email verified. You can now log in."})


class MobileBotVictoryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            completed_level = int(request.data.get("level", 0))
        except (TypeError, ValueError):
            completed_level = 0
        user = request.user
        if completed_level == user.bot_level and user.bot_level < 10:
            user.bot_level += 1
            user.save(update_fields=["bot_level"])
        return Response({"bot_level": user.bot_level})
