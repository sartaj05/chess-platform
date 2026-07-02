# Generated for Module 4 analysis and opening explorer.
from __future__ import annotations

import uuid
from decimal import Decimal

import chess
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


OPENINGS = [
    ("C20", "King's Pawn Game", ["e2e4"], "1. e4", 120000, Decimal("38.00"), Decimal("31.00"), Decimal("31.00")),
    ("B00", "Owen Defense", ["e2e4", "b7b6"], "1. e4 b6", 1600, Decimal("40.00"), Decimal("28.00"), Decimal("32.00")),
    ("C50", "Italian Game", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"], "1. e4 e5 2. Nf3 Nc6 3. Bc4", 38000, Decimal("39.00"), Decimal("33.00"), Decimal("28.00")),
    ("C60", "Ruy Lopez", ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"], "1. e4 e5 2. Nf3 Nc6 3. Bb5", 52000, Decimal("38.00"), Decimal("36.00"), Decimal("26.00")),
    ("B20", "Sicilian Defense", ["e2e4", "c7c5"], "1. e4 c5", 90000, Decimal("36.00"), Decimal("31.00"), Decimal("33.00")),
    ("B30", "Sicilian Defense: Old Sicilian", ["e2e4", "c7c5", "g1f3", "b8c6"], "1. e4 c5 2. Nf3 Nc6", 18000, Decimal("37.00"), Decimal("30.00"), Decimal("33.00")),
    ("B90", "Sicilian Defense: Najdorf", ["e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "a7a6"], "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6", 15000, Decimal("37.00"), Decimal("32.00"), Decimal("31.00")),
    ("C00", "French Defense", ["e2e4", "e7e6"], "1. e4 e6", 42000, Decimal("36.00"), Decimal("33.00"), Decimal("31.00")),
    ("B10", "Caro-Kann Defense", ["e2e4", "c7c6"], "1. e4 c6", 39000, Decimal("36.00"), Decimal("35.00"), Decimal("29.00")),
    ("B01", "Scandinavian Defense", ["e2e4", "d7d5"], "1. e4 d5", 21000, Decimal("39.00"), Decimal("29.00"), Decimal("32.00")),
    ("D00", "Queen's Pawn Game", ["d2d4"], "1. d4", 110000, Decimal("37.00"), Decimal("35.00"), Decimal("28.00")),
    ("D06", "Queen's Gambit", ["d2d4", "d7d5", "c2c4"], "1. d4 d5 2. c4", 70000, Decimal("38.00"), Decimal("36.00"), Decimal("26.00")),
    ("E00", "Indian Game", ["d2d4", "g8f6", "c2c4"], "1. d4 Nf6 2. c4", 65000, Decimal("37.00"), Decimal("36.00"), Decimal("27.00")),
    ("E60", "King's Indian Defense", ["d2d4", "g8f6", "c2c4", "g7g6"], "1. d4 Nf6 2. c4 g6", 28000, Decimal("38.00"), Decimal("32.00"), Decimal("30.00")),
    ("A40", "Modern Defense", ["d2d4", "g7g6"], "1. d4 g6", 6500, Decimal("39.00"), Decimal("29.00"), Decimal("32.00")),
    ("A04", "Reti Opening", ["g1f3"], "1. Nf3", 27000, Decimal("36.00"), Decimal("37.00"), Decimal("27.00")),
    ("A10", "English Opening", ["c2c4"], "1. c4", 45000, Decimal("37.00"), Decimal("36.00"), Decimal("27.00")),
]


def fen_after_moves(moves_uci):
    board = chess.Board()
    for uci in moves_uci:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            break
        board.push(move)
    return board.fen()


def seed_openings(apps, schema_editor):
    OpeningBookLine = apps.get_model("analysis", "OpeningBookLine")
    for eco, name, moves_uci, pgn_prefix, frequency, white_win, draw, black_win in OPENINGS:
        OpeningBookLine.objects.get_or_create(
            eco=eco,
            pgn_prefix=pgn_prefix,
            defaults={
                "name": name,
                "moves_uci": moves_uci,
                "moves_san": pgn_prefix,
                "fen_after": fen_after_moves(moves_uci),
                "frequency": frequency,
                "white_win_rate": white_win,
                "draw_rate": draw,
                "black_win_rate": black_win,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("games", "0001_initial"),
        ("stockfish", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="GameAnalysisJob",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("analysis_type", models.CharField(choices=[("quick", "Quick"), ("deep", "Deep"), ("imported", "Imported")], default="quick", max_length=20)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], db_index=True, default="queued", max_length=20)),
                ("depth", models.PositiveSmallIntegerField(default=10)),
                ("movetime_ms", models.PositiveIntegerField(default=500)),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("summary", models.JSONField(blank=True, default=dict)),
                ("engine_profile", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="analysis_jobs", to="stockfish.stockfishengineprofile")),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="analysis_jobs", to="games.game")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="analysis_jobs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="OpeningBookLine",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("eco", models.CharField(db_index=True, max_length=8)),
                ("name", models.CharField(db_index=True, max_length=160)),
                ("moves_uci", models.JSONField(default=list)),
                ("moves_san", models.CharField(max_length=500)),
                ("pgn_prefix", models.CharField(db_index=True, max_length=500)),
                ("fen_after", models.CharField(max_length=180)),
                ("frequency", models.PositiveIntegerField(default=1)),
                ("white_win_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("draw_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("black_win_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
            ],
            options={"ordering": ["eco", "name"]},
        ),
        migrations.CreateModel(
            name="OpeningExplorerQuery",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("moves_uci", models.JSONField(blank=True, default=list)),
                ("fen", models.CharField(blank=True, max_length=180)),
                ("result_count", models.PositiveIntegerField(default=0)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="opening_queries", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PositionAnalysis",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("fen", models.CharField(db_index=True, max_length=180)),
                ("side_to_move", models.CharField(db_index=True, max_length=5)),
                ("depth", models.PositiveSmallIntegerField(default=0)),
                ("movetime_ms", models.PositiveIntegerField(default=0)),
                ("multipv", models.PositiveSmallIntegerField(default=1)),
                ("bestmove_uci", models.CharField(blank=True, max_length=8)),
                ("bestmove_san", models.CharField(blank=True, max_length=32)),
                ("score_cp", models.IntegerField(blank=True, null=True)),
                ("score_white_cp", models.IntegerField(blank=True, null=True)),
                ("mate_score", models.IntegerField(blank=True, null=True)),
                ("pv", models.JSONField(blank=True, default=list)),
                ("raw_engine", models.JSONField(blank=True, default=dict)),
                ("game", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="position_analyses", to="games.game")),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="positions", to="analysis.gameanalysisjob")),
                ("move", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="position_analyses", to="games.gamemove")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="MoveReview",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("ply_number", models.PositiveIntegerField(db_index=True)),
                ("move_uci", models.CharField(max_length=8)),
                ("move_san", models.CharField(max_length=32)),
                ("classification", models.CharField(choices=[("book", "Book"), ("best", "Best"), ("excellent", "Excellent"), ("good", "Good"), ("inaccuracy", "Inaccuracy"), ("mistake", "Mistake"), ("blunder", "Blunder"), ("forced", "Forced"), ("unknown", "Unknown")], db_index=True, max_length=20)),
                ("before_score_white_cp", models.IntegerField(blank=True, null=True)),
                ("after_score_white_cp", models.IntegerField(blank=True, null=True)),
                ("bestmove_uci", models.CharField(blank=True, max_length=8)),
                ("bestmove_san", models.CharField(blank=True, max_length=32)),
                ("score_loss_cp", models.PositiveIntegerField(default=0)),
                ("comment", models.CharField(blank=True, max_length=255)),
                ("fen_before", models.CharField(max_length=180)),
                ("fen_after", models.CharField(max_length=180)),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="move_reviews", to="games.game")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="move_reviews", to="analysis.gameanalysisjob")),
                ("move", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="review", to="games.gamemove")),
            ],
            options={"ordering": ["ply_number"]},
        ),
        migrations.AddIndex(model_name="gameanalysisjob", index=models.Index(fields=["game", "status"], name="analysis_job_game_status_idx")),
        migrations.AddIndex(model_name="gameanalysisjob", index=models.Index(fields=["status", "created_at"], name="analysis_job_status_time_idx")),
        migrations.AddIndex(model_name="openingbookline", index=models.Index(fields=["is_active", "eco"], name="analysis_opening_active_eco_idx")),
        migrations.AddIndex(model_name="openingbookline", index=models.Index(fields=["is_active", "name"], name="analysis_opening_active_name_idx")),
        migrations.AddIndex(model_name="openingexplorerquery", index=models.Index(fields=["created_at"], name="analysis_opening_query_time_idx")),
        migrations.AddIndex(model_name="positionanalysis", index=models.Index(fields=["game", "created_at"], name="analysis_pos_game_time_idx")),
        migrations.AddIndex(model_name="positionanalysis", index=models.Index(fields=["job", "created_at"], name="analysis_pos_job_time_idx")),
        migrations.AddIndex(model_name="movereview", index=models.Index(fields=["game", "ply_number"], name="analysis_review_game_ply_idx")),
        migrations.AddIndex(model_name="movereview", index=models.Index(fields=["classification", "created_at"], name="analysis_review_class_time_idx")),
        migrations.AddConstraint(model_name="gameanalysisjob", constraint=models.CheckConstraint(condition=models.Q(("depth__gte", 1)), name="analysis_depth_min_one")),
        migrations.AddConstraint(model_name="gameanalysisjob", constraint=models.CheckConstraint(condition=models.Q(("progress__lte", 100)), name="analysis_progress_max_100")),
        migrations.AddConstraint(model_name="openingbookline", constraint=models.UniqueConstraint(fields=("eco", "pgn_prefix"), name="analysis_unique_eco_prefix")),
        migrations.AddConstraint(model_name="movereview", constraint=models.UniqueConstraint(fields=("job", "ply_number"), name="analysis_unique_review_job_ply")),
        migrations.RunPython(seed_openings, migrations.RunPython.noop),
    ]
