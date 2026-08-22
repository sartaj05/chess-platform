from __future__ import annotations

from django.db import migrations

STARTER_PUZZLES = [
    ("Control the centre", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", ["e2e4", "e7e5", "g1f3"], 700, "beginner", ["development", "centre"]),
    ("Queen's pawn development", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", ["d2d4", "d7d5", "c2c4"], 760, "beginner", ["development", "centre"]),
    ("Develop with tempo", "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", ["g1f3", "b8c6", "f1b5"], 850, "beginner", ["development", "pin"]),
    ("Challenge the centre", "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2", ["b8c6", "f1b5", "a7a6"], 950, "intermediate", ["development", "tempo"]),
    ("Build the Italian position", "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3", ["f1c4", "g8f6", "d2d3"], 1050, "intermediate", ["development", "king safety"]),
    ("Prepare to castle", "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3", ["g8f6", "d2d3", "f8c5"], 1150, "intermediate", ["development", "king safety"]),
]


def seed_puzzles(apps, schema_editor):
    Puzzle = apps.get_model("puzzles", "Puzzle")
    for title, fen, moves, rating, difficulty, themes in STARTER_PUZZLES:
        Puzzle.objects.get_or_create(
            title=title,
            defaults={
                "initial_fen": fen,
                "solution_moves": moves,
                "rating": rating,
                "difficulty": difficulty,
                "themes": themes,
                "explanation": "Follow the forcing continuation and improve the position.",
                "is_published": True,
            },
        )


def remove_starter_puzzles(apps, schema_editor):
    Puzzle = apps.get_model("puzzles", "Puzzle")
    Puzzle.objects.filter(title__in=[item[0] for item in STARTER_PUZZLES]).delete()


class Migration(migrations.Migration):
    dependencies = [("puzzles", "0002_puzzleattempt_rating_applied_and_more")]
    operations = [migrations.RunPython(seed_puzzles, remove_starter_puzzles)]
