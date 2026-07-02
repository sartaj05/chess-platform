# Generated for Module 3 gameplay foundation.
from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("rooms", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Game",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("variant", models.CharField(choices=[("standard", "Standard")], default="standard", max_length=24)),
                ("status", models.CharField(choices=[("created", "Created"), ("active", "Active"), ("paused", "Paused"), ("finished", "Finished"), ("aborted", "Aborted")], db_index=True, default="created", max_length=16)),
                ("rated", models.BooleanField(db_index=True, default=False)),
                ("allow_spectators", models.BooleanField(default=True)),
                ("white_guest_key", models.CharField(blank=True, db_index=True, max_length=64)),
                ("black_guest_key", models.CharField(blank=True, db_index=True, max_length=64)),
                ("white_display_name", models.CharField(max_length=80)),
                ("black_display_name", models.CharField(max_length=80)),
                ("initial_fen", models.CharField(default="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", max_length=150)),
                ("current_fen", models.CharField(default="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", max_length=150)),
                ("initial_pgn", models.TextField(blank=True)),
                ("cached_pgn", models.TextField(blank=True)),
                ("turn", models.CharField(choices=[("white", "White"), ("black", "Black")], db_index=True, default="white", max_length=5)),
                ("fullmove_number", models.PositiveIntegerField(default=1)),
                ("ply_count", models.PositiveIntegerField(db_index=True, default=0)),
                ("last_move_uci", models.CharField(blank=True, max_length=8)),
                ("last_move_san", models.CharField(blank=True, max_length=32)),
                ("clock_initial_ms", models.PositiveIntegerField(default=300000)),
                ("increment_ms", models.PositiveIntegerField(default=0)),
                ("delay_ms", models.PositiveIntegerField(default=0)),
                ("white_time_ms", models.PositiveIntegerField(default=300000)),
                ("black_time_ms", models.PositiveIntegerField(default=300000)),
                ("clock_started_at", models.DateTimeField(blank=True, null=True)),
                ("last_move_at", models.DateTimeField(blank=True, null=True)),
                ("result", models.CharField(choices=[("*", "Ongoing"), ("1-0", "White wins"), ("0-1", "Black wins"), ("1/2-1/2", "Draw")], db_index=True, default="*", max_length=12)),
                ("termination", models.CharField(choices=[("none", "None"), ("checkmate", "Checkmate"), ("resignation", "Resignation"), ("agreement", "Agreement"), ("stalemate", "Stalemate"), ("insufficient_material", "Insufficient material"), ("seventyfive_moves", "Seventy-five moves"), ("fivefold_repetition", "Fivefold repetition"), ("fifty_move_rule", "Fifty-move rule"), ("threefold_repetition", "Threefold repetition"), ("timeout", "Timeout"), ("aborted", "Aborted"), ("imported", "Imported")], default="none", max_length=32)),
                ("winner_color", models.CharField(blank=True, choices=[("white", "White"), ("black", "Black")], max_length=5)),
                ("started_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("draw_offer_by", models.CharField(blank=True, choices=[("white", "White"), ("black", "Black")], max_length=5)),
                ("draw_offer_at", models.DateTimeField(blank=True, null=True)),
                ("takeback_offer_by", models.CharField(blank=True, choices=[("white", "White"), ("black", "Black")], max_length=5)),
                ("takeback_offer_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("black_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="black_games", to=settings.AUTH_USER_MODEL)),
                ("room", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="game", to="rooms.room")),
                ("white_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="white_games", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="GameEvent",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(choices=[("game.created", "Game created"), ("game.started", "Game started"), ("move.played", "Move played"), ("game.resigned", "Game resigned"), ("game.aborted", "Game aborted"), ("draw.offered", "Draw offered"), ("draw.accepted", "Draw accepted"), ("draw.declined", "Draw declined"), ("takeback.offered", "Takeback offered"), ("takeback.accepted", "Takeback accepted"), ("takeback.declined", "Takeback declined"), ("clock.timeout", "Clock timeout"), ("game.chat", "Game chat"), ("game.error", "Game error")], db_index=True, max_length=64)),
                ("actor_guest_key", models.CharField(blank=True, db_index=True, max_length=64)),
                ("actor_display_name", models.CharField(blank=True, max_length=80)),
                ("actor_color", models.CharField(blank=True, max_length=5)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("actor_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="game_events", to=settings.AUTH_USER_MODEL)),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="games.game")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="GameMove",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("ply_number", models.PositiveIntegerField(db_index=True)),
                ("move_number", models.PositiveIntegerField(db_index=True)),
                ("color", models.CharField(choices=[("white", "White"), ("black", "Black")], db_index=True, max_length=5)),
                ("uci", models.CharField(max_length=8)),
                ("san", models.CharField(max_length=32)),
                ("from_square", models.CharField(max_length=2)),
                ("to_square", models.CharField(max_length=2)),
                ("promotion", models.CharField(blank=True, max_length=1)),
                ("fen_before", models.CharField(max_length=150)),
                ("fen_after", models.CharField(max_length=150)),
                ("white_time_ms", models.PositiveIntegerField(default=0)),
                ("black_time_ms", models.PositiveIntegerField(default=0)),
                ("played_by_guest_key", models.CharField(blank=True, max_length=64)),
                ("played_by_display_name", models.CharField(blank=True, max_length=80)),
                ("client_lag_ms", models.PositiveIntegerField(default=0)),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="moves", to="games.game")),
                ("played_by_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="played_moves", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["ply_number"]},
        ),
        migrations.AddIndex(model_name="game", index=models.Index(fields=["status", "created_at"], name="games_game_status_created_idx")),
        migrations.AddIndex(model_name="game", index=models.Index(fields=["rated", "status"], name="games_game_rated_status_idx")),
        migrations.AddIndex(model_name="game", index=models.Index(fields=["white_user", "created_at"], name="games_game_white_user_idx")),
        migrations.AddIndex(model_name="game", index=models.Index(fields=["black_user", "created_at"], name="games_game_black_user_idx")),
        migrations.AddIndex(model_name="game", index=models.Index(fields=["room"], name="games_game_room_idx")),
        migrations.AddConstraint(model_name="game", constraint=models.CheckConstraint(condition=models.Q(("clock_initial_ms__gte", 0)), name="games_clock_initial_nonnegative")),
        migrations.AddConstraint(model_name="game", constraint=models.CheckConstraint(condition=models.Q(("white_time_ms__gte", 0)), name="games_white_time_nonnegative")),
        migrations.AddConstraint(model_name="game", constraint=models.CheckConstraint(condition=models.Q(("black_time_ms__gte", 0)), name="games_black_time_nonnegative")),
        migrations.AddIndex(model_name="gamemove", index=models.Index(fields=["game", "ply_number"], name="games_move_game_ply_idx")),
        migrations.AddIndex(model_name="gamemove", index=models.Index(fields=["game", "move_number"], name="games_move_game_move_idx")),
        migrations.AddConstraint(model_name="gamemove", constraint=models.UniqueConstraint(fields=("game", "ply_number"), name="games_unique_ply_per_game")),
        migrations.AddIndex(model_name="gameevent", index=models.Index(fields=["game", "event_type", "created_at"], name="games_event_game_type_idx")),
        migrations.AddIndex(model_name="gameevent", index=models.Index(fields=["game", "created_at"], name="games_event_game_time_idx")),
    ]
