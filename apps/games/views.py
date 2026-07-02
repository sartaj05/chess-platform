from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView, View

from apps.games.forms import FenImportForm, SamePcGameForm
from apps.games.models import Game
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
