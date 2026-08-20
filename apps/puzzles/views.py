from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, TemplateView
import chess

from .forms import PuzzleMoveForm
from .models import Puzzle
from .services import get_attempt, reset_attempt, submit_move


class PuzzleListView(LoginRequiredMixin, ListView):
    model = Puzzle
    template_name = "puzzles/list.html"
    context_object_name = "puzzles"
    paginate_by = 24

    def get_queryset(self):
        queryset = Puzzle.objects.filter(is_published=True)
        difficulty = self.request.GET.get("difficulty", "")
        if difficulty in Puzzle.Difficulty.values:
            queryset = queryset.filter(difficulty=difficulty)
        return queryset.prefetch_related("attempts")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempts = {attempt.puzzle_id: attempt for attempt in self.request.user.puzzle_attempts.all()}
        context["puzzle_rows"] = [{"puzzle": puzzle, "attempt": attempts.get(puzzle.pk)} for puzzle in context["puzzles"]]
        context["difficulties"] = Puzzle.Difficulty.choices
        context["selected_difficulty"] = self.request.GET.get("difficulty", "")
        return context


class PuzzleDetailView(LoginRequiredMixin, TemplateView):
    template_name = "puzzles/detail.html"

    def _puzzle(self) -> Puzzle:
        return get_object_or_404(Puzzle, pk=self.kwargs["pk"], is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        puzzle = self._puzzle()
        attempt = get_attempt(puzzle=puzzle, user=self.request.user)
        board = chess.Board(attempt.current_fen)
        legal_moves: dict[str, dict[str, str]] = {}
        for move in board.legal_moves:
            source = chess.square_name(move.from_square)
            destination = chess.square_name(move.to_square)
            if destination not in legal_moves.setdefault(source, {}) or move.promotion == chess.QUEEN:
                legal_moves[source][destination] = move.uci()
        symbols = {"P":"♙","N":"♘","B":"♗","R":"♖","Q":"♕","K":"♔","p":"♟","n":"♞","b":"♝","r":"♜","q":"♛","k":"♚"}
        context.update(
            puzzle=puzzle, attempt=attempt, move_form=PuzzleMoveForm(), legal_moves=legal_moves,
            side_to_move="White" if board.turn == chess.WHITE else "Black",
            player_move_number=(attempt.next_move_index // 2) + 1,
            total_player_moves=(len(puzzle.solution_moves) + 1) // 2,
            next_puzzle=Puzzle.objects.filter(is_published=True, rating__gte=puzzle.rating).exclude(pk=puzzle.pk).order_by("rating", "pk").first()
            or Puzzle.objects.filter(is_published=True).exclude(pk=puzzle.pk).order_by("rating", "pk").first(),
            board_squares=[{"name": chess.square_name(square), "piece": symbols.get(board.piece_at(square).symbol(), "") if board.piece_at(square) else "", "dark": (file + rank) % 2 == 0} for rank in range(7, -1, -1) for file in range(8) for square in [chess.square(file, rank)]],
        )
        return context

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        puzzle = self._puzzle()
        attempt = get_attempt(puzzle=puzzle, user=request.user)
        form = PuzzleMoveForm(request.POST)
        if form.is_valid():
            try:
                correct, reply = submit_move(attempt=attempt, move_text=form.cleaned_data["move"])
                if correct:
                    messages.success(request, "Correct move." + (f" Opponent replied {reply}." if reply else " Puzzle solved!"))
                else:
                    messages.error(request, "That is not the puzzle move. Try again.")
            except ValidationError as exc:
                messages.info(request, "; ".join(exc.messages))
        else:
            messages.error(request, "Enter a move in UCI format, for example e2e4.")
        return redirect("puzzles:detail", pk=puzzle.pk)


class PuzzleResetView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        puzzle = get_object_or_404(Puzzle, pk=pk, is_published=True)
        reset_attempt(attempt=get_attempt(puzzle=puzzle, user=request.user))
        messages.success(request, "Puzzle attempt reset.")
        return redirect("puzzles:detail", pk=puzzle.pk)
