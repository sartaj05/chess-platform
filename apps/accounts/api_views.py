from drf_spectacular.utils import extend_schema
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

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


class PuzzleListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.puzzles.models import Puzzle
        rows = Puzzle.objects.filter(is_published=True).order_by("rating")[:100]
        daily = Puzzle.objects.filter(is_published=True).order_by("id")[timezone.localdate().toordinal() % max(Puzzle.objects.filter(is_published=True).count(), 1)] if rows else None
        leaders = User.objects.filter(is_active=True).order_by("-puzzle_rating", "display_name")[:20]
        return Response({"daily_id": daily.pk if daily else None, "puzzle_rating": request.user.puzzle_rating, "streak": request.user.puzzle_streak, "best_streak": request.user.puzzle_best_streak, "leaderboard": [{"name":u.display_name,"rating":u.puzzle_rating,"streak":u.puzzle_streak} for u in leaders], "results":[{"id": row.pk, "title": row.title, "fen": row.initial_fen, "rating": row.rating, "difficulty": row.difficulty, "themes": row.themes} for row in rows]})


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
        return Response({"correct": correct, "reply": reply, "fen": attempt.current_fen, "status": attempt.status, "mistakes": attempt.mistakes, "rating_change": attempt.rating_change, "puzzle_rating": request.user.puzzle_rating, "streak": request.user.puzzle_streak})


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
