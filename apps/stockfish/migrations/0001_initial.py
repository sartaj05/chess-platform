# Generated for Module 4 Stockfish integration.
from __future__ import annotations

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_default_profile(apps, schema_editor):
    StockfishEngineProfile = apps.get_model("stockfish", "StockfishEngineProfile")
    StockfishEngineProfile.objects.get_or_create(
        name="Default Offline Stockfish",
        defaults={
            "binary_path": getattr(settings, "STOCKFISH_BINARY", "/usr/games/stockfish"),
            "default_depth": getattr(settings, "STOCKFISH_DEFAULT_DEPTH", 12),
            "default_movetime_ms": getattr(settings, "STOCKFISH_DEFAULT_MOVETIME_MS", 750),
            "skill_level": 20,
            "threads": getattr(settings, "STOCKFISH_THREADS", 1),
            "hash_mb": getattr(settings, "STOCKFISH_HASH_MB", 64),
            "is_active": True,
        },
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("games", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StockfishEngineProfile",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=80, unique=True)),
                ("binary_path", models.CharField(default="/usr/games/stockfish", max_length=500)),
                ("default_depth", models.PositiveSmallIntegerField(default=12)),
                ("default_movetime_ms", models.PositiveIntegerField(default=750)),
                ("skill_level", models.PositiveSmallIntegerField(default=20)),
                ("threads", models.PositiveSmallIntegerField(default=1)),
                ("hash_mb", models.PositiveIntegerField(default=64)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="StockfishRun",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("fen", models.CharField(max_length=180)),
                ("command_type", models.CharField(default="position_analysis", max_length=40)),
                ("depth", models.PositiveSmallIntegerField(default=0)),
                ("movetime_ms", models.PositiveIntegerField(default=0)),
                ("bestmove", models.CharField(blank=True, max_length=8)),
                ("ponder", models.CharField(blank=True, max_length=8)),
                ("score_cp", models.IntegerField(blank=True, null=True)),
                ("mate_score", models.IntegerField(blank=True, null=True)),
                ("nodes", models.BigIntegerField(default=0)),
                ("nps", models.BigIntegerField(default=0)),
                ("raw_info", models.JSONField(blank=True, default=dict)),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(choices=[("success", "Success"), ("failed", "Failed"), ("unavailable", "Unavailable")], db_index=True, default="success", max_length=20)),
                ("error_message", models.TextField(blank=True)),
                ("game", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="engine_runs", to="games.game")),
                ("profile", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="runs", to="stockfish.stockfishengineprofile")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="stockfishengineprofile", index=models.Index(fields=["is_active", "name"], name="stockfish_profile_active_idx")),
        migrations.AddIndex(model_name="stockfishrun", index=models.Index(fields=["status", "created_at"], name="stockfish_run_status_time_idx")),
        migrations.AddIndex(model_name="stockfishrun", index=models.Index(fields=["game", "created_at"], name="stockfish_run_game_time_idx")),
        migrations.AddConstraint(model_name="stockfishengineprofile", constraint=models.CheckConstraint(condition=models.Q(("default_depth__gte", 1)), name="stockfish_depth_min_one")),
        migrations.AddConstraint(model_name="stockfishengineprofile", constraint=models.CheckConstraint(condition=models.Q(("skill_level__lte", 20)), name="stockfish_skill_max_twenty")),
        migrations.AddConstraint(model_name="stockfishengineprofile", constraint=models.CheckConstraint(condition=models.Q(("threads__gte", 1)), name="stockfish_threads_min_one")),
        migrations.AddConstraint(model_name="stockfishengineprofile", constraint=models.CheckConstraint(condition=models.Q(("hash_mb__gte", 1)), name="stockfish_hash_min_one")),
        migrations.RunPython(seed_default_profile, migrations.RunPython.noop),
    ]
