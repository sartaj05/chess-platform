from __future__ import annotations

import chess
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User

from .models import Puzzle, PuzzleAttempt


def get_attempt(*, puzzle: Puzzle, user: User) -> PuzzleAttempt:
    attempt, _ = PuzzleAttempt.objects.get_or_create(
        puzzle=puzzle,
        user=user,
        defaults={"current_fen": puzzle.initial_fen},
    )
    return attempt


@transaction.atomic
def submit_move(*, attempt: PuzzleAttempt, move_text: str) -> tuple[bool, str | None]:
    if attempt.status == PuzzleAttempt.Status.SOLVED:
        raise ValidationError("This puzzle is already solved.")
    expected = attempt.puzzle.solution_moves[attempt.next_move_index]
    submitted = move_text.strip().lower()
    if submitted != expected:
        attempt.mistakes += 1
        attempt.save(update_fields=["mistakes", "updated_at"])
        return False, None

    board = chess.Board(attempt.current_fen)
    board.push_uci(submitted)
    attempt.next_move_index += 1
    reply = None
    if attempt.next_move_index < len(attempt.puzzle.solution_moves):
        reply = attempt.puzzle.solution_moves[attempt.next_move_index]
        board.push_uci(reply)
        attempt.next_move_index += 1
    attempt.current_fen = board.fen()
    if attempt.next_move_index >= len(attempt.puzzle.solution_moves):
        attempt.status = PuzzleAttempt.Status.SOLVED
        attempt.solved_at = timezone.now()
    attempt.save(update_fields=["current_fen", "next_move_index", "status", "solved_at", "updated_at"])
    return True, reply


def reset_attempt(*, attempt: PuzzleAttempt) -> PuzzleAttempt:
    attempt.current_fen = attempt.puzzle.initial_fen
    attempt.next_move_index = 0
    attempt.mistakes = 0
    attempt.status = PuzzleAttempt.Status.IN_PROGRESS
    attempt.solved_at = None
    attempt.save(
        update_fields=["current_fen", "next_move_index", "mistakes", "status", "solved_at", "updated_at"]
    )
    return attempt
