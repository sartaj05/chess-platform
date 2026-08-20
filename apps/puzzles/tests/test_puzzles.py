from __future__ import annotations

import chess
import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.games.models import STARTING_FEN
from apps.puzzles.models import Puzzle, PuzzleAttempt, PuzzleCourse, PuzzleCourseItem


@pytest.fixture
def puzzle_user(db):
    return User.objects.create_user(email="solver@example.com", password="test-pass-123")


@pytest.fixture
def puzzle(db):
    return Puzzle.objects.create(
        title="Opening development",
        initial_fen=STARTING_FEN,
        solution_moves=["e2e4", "e7e5", "g1f3"],
        rating=800,
        difficulty=Puzzle.Difficulty.BEGINNER,
        themes=["development"],
    )


def test_puzzles_require_login(client, puzzle):
    assert client.get(reverse("puzzles:list")).status_code == 302
    assert client.get(reverse("puzzles:detail", args=[puzzle.pk])).status_code == 302


def test_puzzle_validates_fen_and_solution(db):
    invalid = Puzzle(title="Invalid", initial_fen="not-a-fen", solution_moves=["e2e4"])
    with pytest.raises(ValidationError):
        invalid.full_clean()

    illegal = Puzzle(title="Illegal", initial_fen=STARTING_FEN, solution_moves=["e2e5"])
    with pytest.raises(ValidationError):
        illegal.full_clean()


def test_mobile_puzzle_courses_and_solution_explanation(puzzle_user, puzzle):
    puzzle.explanation = "Control the centre, then develop with tempo."
    puzzle.save(update_fields=["explanation"])
    course = PuzzleCourse.objects.create(title="Opening principles", slug="opening-principles", theme="development")
    PuzzleCourseItem.objects.create(course=course, puzzle=puzzle, position=1)
    client = APIClient()
    client.force_authenticate(puzzle_user)
    listing = client.get("/api/accounts/puzzles/")
    assert listing.status_code == 200
    assert listing.data["courses"][0]["puzzle_ids"] == [puzzle.pk]
    assert client.post(f"/api/accounts/puzzles/{puzzle.pk}/play/", {"move": "e2e4"}).data["explanation"] == ""
    solved = client.post(f"/api/accounts/puzzles/{puzzle.pk}/play/", {"move": "g1f3"})
    assert solved.data["status"] == "solved"
    assert "Control the centre" in solved.data["explanation"]


def test_correct_moves_advance_and_solve(client, puzzle_user, puzzle):
    client.force_login(puzzle_user)
    response = client.post(reverse("puzzles:detail", args=[puzzle.pk]), {"move": "e2e4"})
    assert response.status_code == 302
    attempt = PuzzleAttempt.objects.get(user=puzzle_user, puzzle=puzzle)
    assert attempt.next_move_index == 2
    assert attempt.status == PuzzleAttempt.Status.IN_PROGRESS
    board = chess.Board(attempt.current_fen)
    assert board.piece_at(chess.E4) == chess.Piece(chess.PAWN, chess.WHITE)
    assert board.piece_at(chess.E5) == chess.Piece(chess.PAWN, chess.BLACK)

    client.post(reverse("puzzles:detail", args=[puzzle.pk]), {"move": "g1f3"})
    attempt.refresh_from_db()
    assert attempt.status == PuzzleAttempt.Status.SOLVED
    assert attempt.solved_at is not None


def test_wrong_move_records_mistake_without_advancing(client, puzzle_user, puzzle):
    client.force_login(puzzle_user)
    client.post(reverse("puzzles:detail", args=[puzzle.pk]), {"move": "d2d4"})
    attempt = PuzzleAttempt.objects.get(user=puzzle_user, puzzle=puzzle)
    assert attempt.mistakes == 1
    assert attempt.next_move_index == 0
    assert attempt.current_fen == puzzle.initial_fen


def test_reset_clears_progress(client, puzzle_user, puzzle):
    attempt = PuzzleAttempt.objects.create(
        user=puzzle_user,
        puzzle=puzzle,
        current_fen=puzzle.initial_fen,
        next_move_index=2,
        mistakes=3,
    )
    client.force_login(puzzle_user)
    response = client.post(reverse("puzzles:reset", args=[puzzle.pk]))
    assert response.status_code == 302
    attempt.refresh_from_db()
    assert attempt.next_move_index == 0
    assert attempt.mistakes == 0
    assert attempt.status == PuzzleAttempt.Status.IN_PROGRESS


def test_unpublished_puzzle_is_not_accessible(client, puzzle_user, puzzle):
    puzzle.is_published = False
    puzzle.save(update_fields=["is_published"])
    client.force_login(puzzle_user)
    assert client.get(reverse("puzzles:detail", args=[puzzle.pk])).status_code == 404


def test_puzzle_detail_exposes_only_legal_visual_moves(client, puzzle_user, puzzle):
    client.force_login(puzzle_user)
    response = client.get(reverse("puzzles:detail", args=[puzzle.pk]))

    assert response.status_code == 200
    assert response.context["legal_moves"]["e2"] == {"e3": "e2e3", "e4": "e2e4"}
    assert "f2" not in response.context["legal_moves"]["e2"]
    assert response.context["side_to_move"] == "White"
    assert response.context["player_move_number"] == 1
    assert response.context["total_player_moves"] == 2
    assert b"Select a piece, then a highlighted square" in response.content


def test_solved_puzzle_offers_next_puzzle(client, puzzle_user, puzzle):
    Puzzle.objects.create(
        title="Next lesson",
        initial_fen=STARTING_FEN,
        solution_moves=["d2d4"],
        rating=900,
        difficulty=Puzzle.Difficulty.BEGINNER,
    )
    client.force_login(puzzle_user)
    client.post(reverse("puzzles:detail", args=[puzzle.pk]), {"move": "e2e4"})
    client.post(reverse("puzzles:detail", args=[puzzle.pk]), {"move": "g1f3"})

    response = client.get(reverse("puzzles:detail", args=[puzzle.pk]))
    assert response.context["next_puzzle"] is not None
    assert response.context["next_puzzle"] != puzzle
    assert b"Puzzle solved" in response.content
    assert b"Next puzzle" in response.content
