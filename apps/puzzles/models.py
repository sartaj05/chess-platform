from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel


class Puzzle(TimeStampedModel):
    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        EXPERT = "expert", "Expert"

    title = models.CharField(max_length=120)
    initial_fen = models.CharField(max_length=150)
    solution_moves = models.JSONField(default=list, help_text="Ordered UCI moves, starting with the solver's move.")
    rating = models.PositiveSmallIntegerField(default=1200, db_index=True)
    difficulty = models.CharField(max_length=16, choices=Difficulty.choices, default=Difficulty.INTERMEDIATE, db_index=True)
    themes = models.JSONField(default=list, blank=True)
    explanation = models.TextField(blank=True)
    is_published = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["rating", "created_at"]
        indexes = [models.Index(fields=["is_published", "difficulty", "rating"], name="puzzle_public_level_idx")]

    def __str__(self) -> str:
        return f"{self.title} ({self.rating})"

    def clean(self) -> None:
        super().clean()
        import chess

        try:
            board = chess.Board(self.initial_fen)
        except ValueError as exc:
            raise ValidationError({"initial_fen": "Enter a valid FEN position."}) from exc
        if not isinstance(self.solution_moves, list) or not self.solution_moves:
            raise ValidationError({"solution_moves": "Provide at least one UCI move."})
        for move_text in self.solution_moves:
            try:
                move = chess.Move.from_uci(str(move_text))
            except ValueError as exc:
                raise ValidationError({"solution_moves": f"Invalid UCI move: {move_text}."}) from exc
            if move not in board.legal_moves:
                raise ValidationError({"solution_moves": f"Illegal solution move: {move_text}."})
            board.push(move)


class PuzzleCourse(TimeStampedModel):
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.CharField(max_length=300, blank=True)
    theme = models.CharField(max_length=80, db_index=True)
    difficulty = models.CharField(
        max_length=16, choices=Puzzle.Difficulty.choices,
        default=Puzzle.Difficulty.BEGINNER, db_index=True,
    )
    puzzles = models.ManyToManyField(Puzzle, through="PuzzleCourseItem", related_name="courses")
    is_published = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["difficulty", "title"]

    def __str__(self) -> str:
        return self.title


class PuzzleCourseItem(models.Model):
    course = models.ForeignKey(PuzzleCourse, on_delete=models.CASCADE, related_name="items")
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE, related_name="course_items")
    position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["course", "puzzle"], name="puzzle_course_unique_puzzle"),
            models.UniqueConstraint(fields=["course", "position"], name="puzzle_course_unique_position"),
        ]

    def __str__(self) -> str:
        return f"{self.course}: {self.position}. {self.puzzle}"


class PuzzleAttempt(TimeStampedModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        SOLVED = "solved", "Solved"

    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="puzzle_attempts")
    current_fen = models.CharField(max_length=150)
    next_move_index = models.PositiveSmallIntegerField(default=0)
    mistakes = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True)
    solved_at = models.DateTimeField(blank=True, null=True)
    rating_change = models.SmallIntegerField(default=0)
    rating_applied = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [models.UniqueConstraint(fields=["puzzle", "user"], name="puzzle_one_attempt_per_user")]

    def __str__(self) -> str:
        return f"{self.user} / {self.puzzle}"
