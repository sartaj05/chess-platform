from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import FormView, ListView, TemplateView, View

from apps.games.forms import FenImportForm, SamePcGameForm
from apps.games.models import FairPlayAppeal, FairPlayReview, Game
from apps.games.services import (
    abort_game,
    actor_from_request,
    create_game_from_room,
    create_same_pc_game,
    decline_draw,
    import_game_from_fen,
    offer_or_accept_draw,
    pgn_response_text,
    resign_game,
    serialize_game,
)
from apps.rooms.models import Room


class SamePcGameCreateView(FormView):
    template_name = "games/same_pc_new.html"
    form_class = SamePcGameForm

    def form_valid(self, form):
        game = create_same_pc_game(**form.cleaned_data)
        return redirect(game.get_absolute_url())


class FenImportView(FormView):
    template_name = "games/fen_import.html"
    form_class = FenImportForm

    def form_valid(self, form):
        game = import_game_from_fen(request=self.request, **form.cleaned_data)
        messages.success(self.request, "FEN imported successfully.")
        return redirect(game.get_absolute_url())


class StartRoomGameView(View):
    def post(self, request: HttpRequest, code: str) -> HttpResponse:
        room = get_object_or_404(Room.objects.prefetch_related("participants"), code=code.upper())
        try:
            game = create_game_from_room(room=room, request=request)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect(room.get_absolute_url())
        return redirect(game.get_absolute_url())


class GamePlayView(TemplateView):
    template_name = "games/play.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        game = get_object_or_404(
            Game.objects.select_related("room", "white_user", "black_user").prefetch_related("moves"),
            pk=kwargs["pk"],
        )
        context["game"] = game
        context["game_state"] = serialize_game(game, request=self.request)
        return context


class GameStateView(View):
    def get(self, request: HttpRequest, pk: str) -> JsonResponse:
        game = get_object_or_404(Game.objects.select_related("room").prefetch_related("moves"), pk=pk)
        return JsonResponse(serialize_game(game, request=request))


class FenDownloadView(View):
    def get(self, request: HttpRequest, pk: str) -> HttpResponse:
        game = get_object_or_404(Game, pk=pk)
        response = HttpResponse(game.current_fen, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="game-{game.pk}.fen"'
        return response


class PgnDownloadView(View):
    def get(self, request: HttpRequest, pk: str) -> HttpResponse:
        game = get_object_or_404(Game.objects.prefetch_related("moves"), pk=pk)
        response = HttpResponse(pgn_response_text(game), content_type="application/x-chess-pgn; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="game-{game.pk}.pgn"'
        return response


class GameActionMixin(View):
    action_name = ""

    def post(self, request: HttpRequest, pk: str) -> HttpResponse:
        game = get_object_or_404(Game, pk=pk)
        actor = actor_from_request(request, game)
        try:
            self.perform(game, actor)
            messages.success(request, self.success_message())
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect(game.get_absolute_url())

    def perform(self, game, actor):
        raise NotImplementedError

    def success_message(self) -> str:
        return "Game action completed."


class ResignGameView(GameActionMixin):
    def perform(self, game, actor):
        resign_game(game=game, actor=actor)

    def success_message(self) -> str:
        return "Game resigned."


class AbortGameView(GameActionMixin):
    def perform(self, game, actor):
        abort_game(game=game, actor=actor)

    def success_message(self) -> str:
        return "Game aborted."


class DrawOfferView(GameActionMixin):
    def perform(self, game, actor):
        self.result = offer_or_accept_draw(game=game, actor=actor)

    def success_message(self) -> str:
        return "Draw action submitted."


class DeclineDrawView(GameActionMixin):
    def perform(self, game, actor):
        decline_draw(game=game, actor=actor)

    def success_message(self) -> str:
        return "Draw offer declined."


class StaffRequiredMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff


class ModeratorDashboardView(StaffRequiredMixin, ListView):
    template_name = "moderation/dashboard.html"
    context_object_name = "reviews"
    paginate_by = 30

    def get_queryset(self):
        queryset = FairPlayReview.objects.select_related("game", "reviewer").prefetch_related("appeals")
        status = self.request.GET.get("status")
        if status in FairPlayReview.Status.values:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-risk_score", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["open_appeals"] = FairPlayAppeal.objects.filter(
            status__in=[FairPlayAppeal.Status.OPEN, FairPlayAppeal.Status.REVIEWING]
        ).select_related("review__game", "appellant")[:20]
        context["flagged_count"] = FairPlayReview.objects.filter(
            status__in=[FairPlayReview.Status.FLAGGED, FairPlayReview.Status.REVIEWING]
        ).count()
        return context


class ModeratorReviewView(StaffRequiredMixin, View):
    def post(self, request, pk):
        review = get_object_or_404(FairPlayReview, pk=pk)
        status = request.POST.get("status")
        if status not in FairPlayReview.Status.values:
            messages.error(request, "Select a valid case status.")
            return redirect("games:moderator_dashboard")
        review.status = status
        review.moderator_notes = request.POST.get("notes", "").strip()[:4000]
        review.reviewer = request.user
        review.reviewed_at = timezone.now()
        review.save(update_fields=["status", "moderator_notes", "reviewer", "reviewed_at", "updated_at"])
        messages.success(request, "Fair-play case updated.")
        return redirect("games:moderator_dashboard")


class FairPlayAppealCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        review = get_object_or_404(FairPlayReview.objects.select_related("game"), pk=pk)
        game = review.game
        if request.user not in (game.white_user, game.black_user):
            raise PermissionDenied("Only a player in this game can appeal the decision.")
        statement = request.POST.get("statement", "").strip()
        if not statement:
            messages.error(request, "Explain why you are appealing.")
            return redirect(game.get_absolute_url())
        FairPlayAppeal.objects.update_or_create(
            review=review,
            appellant=request.user,
            defaults={"statement": statement[:4000], "status": FairPlayAppeal.Status.OPEN},
        )
        messages.success(request, "Your fair-play appeal was submitted.")
        return redirect(game.get_absolute_url())


class FairPlayAppealResolveView(StaffRequiredMixin, View):
    def post(self, request, pk):
        appeal = get_object_or_404(FairPlayAppeal, pk=pk)
        status = request.POST.get("status")
        allowed = [FairPlayAppeal.Status.REVIEWING, FairPlayAppeal.Status.UPHELD, FairPlayAppeal.Status.OVERTURNED]
        if status not in allowed:
            messages.error(request, "Select a valid appeal outcome.")
            return redirect("games:moderator_dashboard")
        appeal.status = status
        appeal.moderator_response = request.POST.get("response", "").strip()[:4000]
        appeal.resolved_by = request.user
        appeal.resolved_at = timezone.now() if status != FairPlayAppeal.Status.REVIEWING else None
        appeal.save(update_fields=["status", "moderator_response", "resolved_by", "resolved_at", "updated_at"])
        if status == FairPlayAppeal.Status.OVERTURNED:
            appeal.review.status = FairPlayReview.Status.DISMISSED
            appeal.review.save(update_fields=["status", "updated_at"])
        messages.success(request, "Appeal updated.")
        return redirect("games:moderator_dashboard")
