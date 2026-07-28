from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, TemplateView, View

from apps.analysis.forms import OpeningExplorerForm, PositionAnalysisForm, StartAnalysisForm
from apps.analysis.models import GameAnalysisJob
from apps.analysis.services import (
    analyse_position,
    create_analysis_job,
    opening_to_dict,
    search_openings,
    serialize_job,
    serialize_move_review,
)
from apps.analysis.tasks import run_game_analysis_job
from apps.games.models import Game


class AnalysisBoardView(FormView):
    template_name = "analysis/analysis_board.html"
    form_class = PositionAnalysisForm

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("fen"):
            initial["fen"] = self.request.GET["fen"]
        else:
            initial["fen"] = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        return initial

    def form_valid(self, form):
        position = analyse_position(**form.cleaned_data)
        return self.render_to_response(self.get_context_data(form=form, position=position))


class GameReviewView(TemplateView):
    template_name = "analysis/game_review.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        game = get_object_or_404(Game.objects.prefetch_related("moves"), pk=kwargs["pk"])
        job = game.analysis_jobs.prefetch_related("move_reviews").order_by("-created_at").first()
        context.update({"game": game, "job": job, "form": StartAnalysisForm()})
        return context


class StartGameAnalysisView(View):
    def post(self, request: HttpRequest, pk: str) -> HttpResponse:
        game = get_object_or_404(Game, pk=pk)
        form = StartAnalysisForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Invalid analysis options.")
            return redirect("analysis:game_review", pk=game.pk)
        job = create_analysis_job(
            game=game,
            requested_by=request.user,
            analysis_type=form.cleaned_data["analysis_type"],
            depth=form.cleaned_data["depth"],
        )
        run_game_analysis_job.delay(str(job.id))
        messages.success(request, "Game review queued. Refresh this page to see progress.")
        return redirect(job.get_absolute_url())


class AnalysisJobDetailView(TemplateView):
    template_name = "analysis/job_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = get_object_or_404(
            GameAnalysisJob.objects.select_related("game").prefetch_related("move_reviews"), pk=kwargs["pk"]
        )
        context["job"] = job
        context["reviews"] = job.move_reviews.all()
        return context


class AnalysisJobStateView(View):
    def get(self, request: HttpRequest, pk: str) -> JsonResponse:
        job = get_object_or_404(GameAnalysisJob.objects.prefetch_related("move_reviews"), pk=pk)
        return JsonResponse(
            {"job": serialize_job(job), "reviews": [serialize_move_review(item) for item in job.move_reviews.all()]}
        )


class OpeningExplorerView(FormView):
    template_name = "analysis/opening_explorer.html"
    form_class = OpeningExplorerForm

    def form_valid(self, form):
        raw_moves = form.cleaned_data["moves"].replace(",", " ").split()
        openings = search_openings(moves_uci=raw_moves, user=self.request.user, request=self.request)
        return self.render_to_response(self.get_context_data(form=form, openings=openings, raw_moves=raw_moves))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("openings", [])
        context.setdefault("raw_moves", [])
        return context


class OpeningExplorerJsonView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        raw_moves = request.GET.get("moves", "").replace(",", " ").split()
        openings = search_openings(moves_uci=raw_moves, user=request.user, request=request)
        return JsonResponse({"openings": [opening_to_dict(item) for item in openings]})
