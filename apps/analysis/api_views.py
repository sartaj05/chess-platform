from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analysis.models import GameAnalysisJob
from apps.analysis.serializers import GameAnalysisJobSerializer, OpeningBookLineSerializer, PositionAnalysisResultSerializer, PositionAnalysisSerializer, StartAnalysisSerializer
from apps.analysis.services import analyse_position, create_analysis_job, search_openings
from apps.analysis.tasks import run_game_analysis_job
from apps.games.models import Game


class StartGameAnalysisApiView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk: str):
        game = get_object_or_404(Game, pk=pk)
        serializer = StartAnalysisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = create_analysis_job(
            game=game,
            requested_by=request.user,
            analysis_type=serializer.validated_data["analysis_type"],
            depth=serializer.validated_data["depth"],
        )
        run_game_analysis_job.delay(str(job.id))
        return Response(GameAnalysisJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class GameAnalysisJobApiView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk: str):
        job = get_object_or_404(GameAnalysisJob.objects.prefetch_related("move_reviews"), pk=pk)
        return Response(GameAnalysisJobSerializer(job).data)


class PositionAnalysisApiView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PositionAnalysisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        position = analyse_position(**serializer.validated_data)
        return Response(PositionAnalysisResultSerializer(position).data)


class OpeningExplorerApiView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        raw_moves = request.query_params.get("moves", "").replace(",", " ").split()
        openings = search_openings(moves_uci=raw_moves, user=request.user, request=request)
        return Response(OpeningBookLineSerializer(openings, many=True).data)
