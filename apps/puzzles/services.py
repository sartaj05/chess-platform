from __future__ import annotations

from datetime import timedelta

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
        if not attempt.rating_applied:
            user = attempt.user
            expected_score = 1 / (1 + 10 ** ((attempt.puzzle.rating - user.puzzle_rating) / 400))
            change = -max(1, round(24 * expected_score))
            user.puzzle_rating = max(100, user.puzzle_rating + change)
            user.puzzle_streak = 0
            user.save(update_fields=["puzzle_rating", "puzzle_streak"])
            attempt.rating_change = change
            attempt.rating_applied = True
        attempt.save(update_fields=["mistakes", "rating_change", "rating_applied", "updated_at"])
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
        if not attempt.rating_applied:
            user = attempt.user
            expected = 1 / (1 + 10 ** ((attempt.puzzle.rating - user.puzzle_rating) / 400))
            change = max(1, round(24 * (1 - expected)) - min(attempt.mistakes * 2, 8))
            user.puzzle_rating = max(100, user.puzzle_rating + change)
            today = timezone.localdate()
            user.puzzle_streak = user.puzzle_streak + 1 if user.last_puzzle_date == today - timedelta(days=1) else (user.puzzle_streak if user.last_puzzle_date == today else 1)
            user.puzzle_best_streak = max(user.puzzle_best_streak, user.puzzle_streak)
            user.last_puzzle_date = today
            user.save(update_fields=["puzzle_rating", "puzzle_streak", "puzzle_best_streak", "last_puzzle_date"])
            attempt.rating_change, attempt.rating_applied = change, True
    attempt.save(update_fields=["current_fen", "next_move_index", "status", "solved_at", "rating_change", "rating_applied", "updated_at"])
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
