from __future__ import annotations

from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.models import GameAnalysisJob, OpeningBookLine, OpeningPractice
from apps.analysis.serializers import (
    GameAnalysisJobSerializer,
    MoveExplorerSerializer,
    OpeningBookLineSerializer,
    PositionAnalysisResultSerializer,
    PositionAnalysisSerializer,
    StartAnalysisSerializer,
)
from apps.analysis.services import analyse_position, create_analysis_job, personal_opening_statistics, search_openings
from apps.analysis.tasks import run_game_analysis_job
from apps.api.throttles import AnalysisAnonRateThrottle, AnalysisUserRateThrottle
from apps.games.services import visible_games_for_request


class StartGameAnalysisApiView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnalysisAnonRateThrottle, AnalysisUserRateThrottle]

    @extend_schema(
        request=StartAnalysisSerializer,
        responses={status.HTTP_202_ACCEPTED: GameAnalysisJobSerializer},
    )
    def post(self, request, pk: str):
        game = get_object_or_404(visible_games_for_request(request), pk=pk)
        serializer = StartAnalysisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = create_analysis_job(
            game=game,
            requested_by=request.user if request.user.is_authenticated else None,
            analysis_type=serializer.validated_data["analysis_type"],
            depth=serializer.validated_data["depth"],
        )
        run_game_analysis_job.delay(str(job.id))
        return Response(GameAnalysisJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class GameAnalysisJobApiView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=GameAnalysisJobSerializer)
    def get(self, request, pk: str):
        job = get_object_or_404(
            GameAnalysisJob.objects.filter(game__in=visible_games_for_request(request)).prefetch_related(
                "move_reviews"
            ),
            pk=pk,
        )
        return Response(GameAnalysisJobSerializer(job).data)

    def post(self, request, pk: str):
        job = get_object_or_404(GameAnalysisJob.objects.filter(game__in=visible_games_for_request(request)), pk=pk)
        if job.status not in {GameAnalysisJob.Status.FAILED, GameAnalysisJob.Status.CANCELLED}:
            return Response({"detail":"Only failed or cancelled analysis can be retried."}, status=400)
        job.status, job.progress, job.error_message, job.completed_at = GameAnalysisJob.Status.QUEUED, 0, "", None
        job.save(update_fields=["status","progress","error_message","completed_at","updated_at"])
        run_game_analysis_job.delay(str(job.id))
        return Response(GameAnalysisJobSerializer(job).data, status=202)


class PositionAnalysisApiView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnalysisAnonRateThrottle, AnalysisUserRateThrottle]

    @extend_schema(
        request=PositionAnalysisSerializer,
        responses=PositionAnalysisResultSerializer,
    )
    def post(self, request):
        serializer = PositionAnalysisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        position = analyse_position(**serializer.validated_data)
        return Response(PositionAnalysisResultSerializer(position).data)


class MoveExplorerApiView(APIView):
    """Compare a player's candidate with Stockfish and return legal alternatives."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnalysisAnonRateThrottle, AnalysisUserRateThrottle]

    def post(self, request):
        import chess

        serializer = MoveExplorerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            board = chess.Board(data["fen"])
        except ValueError as exc:
            return Response({"detail": f"Invalid FEN: {exc}"}, status=400)
        candidate_uci = data.get("candidate_uci", "")
        candidate = None
        if candidate_uci:
            try:
                candidate = chess.Move.from_uci(candidate_uci)
            except ValueError:
                return Response({"detail": "Enter a valid UCI move."}, status=400)
            if candidate not in board.legal_moves:
                return Response({"detail": "That move is not legal in this position."}, status=400)
        before = analyse_position(
            fen=board.fen(), depth=data["depth"], movetime_ms=data["movetime_ms"]
        )
        result = {
            "fen": board.fen(), "turn": "white" if board.turn else "black",
            "best_move": before.bestmove_uci, "best_move_san": before.bestmove_san,
            "evaluation_cp": before.score_white_cp, "mate": before.mate_score,
            "principal_variation": before.pv,
            "alternatives": [
                {"uci": move.uci(), "san": board.san(move)}
                for move in list(board.legal_moves)[:30]
            ],
        }
        if candidate is not None:
            candidate_san = board.san(candidate)
            board.push(candidate)
            after = analyse_position(
                fen=board.fen(), depth=data["depth"], movetime_ms=data["movetime_ms"]
            )
            before_cp = before.score_white_cp or 0
            after_cp = after.score_white_cp or 0
            mover_white = not board.turn
            loss = max(0, before_cp - after_cp) if mover_white else max(0, after_cp - before_cp)
            result["candidate"] = {
                "uci": candidate_uci, "san": candidate_san, "fen_after": board.fen(),
                "evaluation_after_cp": after.score_white_cp, "centipawn_loss": loss,
                "reply": after.bestmove_uci, "reply_san": after.bestmove_san,
                "verdict": "best" if candidate_uci == before.bestmove_uci else "excellent" if loss <= 30 else "inaccuracy" if loss <= 100 else "mistake",
            }
        return Response(result)


class OpeningExplorerApiView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OpeningBookLineSerializer(many=True))
    def get(self, request):
        raw_moves = request.query_params.get("moves", "").replace(",", " ").split()
        openings = search_openings(moves_uci=raw_moves, user=request.user, request=request)
        return Response(OpeningBookLineSerializer(openings, many=True).data)


class PersonalOpeningStatsApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        return Response(personal_opening_statistics(request.user))


class OpeningPracticeApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        records = {row.opening_id: row for row in OpeningPractice.objects.filter(user=request.user)}
        lines = list(OpeningBookLine.objects.filter(is_active=True).order_by("eco", "name")[:50])
        rows = []
        for line in lines:
            record = records.get(line.pk)
            rows.append({"id": str(line.pk), "eco": line.eco, "name": line.name,
                         "moves_uci": line.moves_uci, "moves_san": line.moves_san,
                         "due": record is None or record.due_at <= now,
                         "due_at": record.due_at if record else now})
        return Response({"due_count": sum(row["due"] for row in rows), "results": rows})

    def post(self, request):
        opening = get_object_or_404(OpeningBookLine, pk=request.data.get("opening_id"), is_active=True)
        quality = max(0, min(int(request.data.get("quality", 0)), 5))
        record, _ = OpeningPractice.objects.get_or_create(user=request.user, opening=opening)
        if quality < 3:
            record.repetitions, record.interval_days = 0, 1
        else:
            record.repetitions += 1
            record.interval_days = 1 if record.repetitions == 1 else 6 if record.repetitions == 2 else max(1, round(record.interval_days * float(record.ease_factor)))
        record.ease_factor = max(1.3, float(record.ease_factor) + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        record.last_quality = quality
        record.due_at = timezone.now() + timedelta(days=record.interval_days)
        record.save()
        return Response({"opening_id": str(opening.pk), "interval_days": record.interval_days, "due_at": record.due_at})
