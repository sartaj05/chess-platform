from __future__ import annotations

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Room",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(db_index=True, max_length=12, unique=True)),
                ("name", models.CharField(blank=True, max_length=120)),
                ("description", models.CharField(blank=True, max_length=240)),
                ("host_guest_key", models.CharField(blank=True, db_index=True, max_length=64)),
                ("host_display_name", models.CharField(blank=True, max_length=80)),
                ("mode", models.CharField(choices=[("online", "Online"), ("lan", "LAN"), ("offline", "Offline"), ("same_pc", "Same computer")], db_index=True, default="online", max_length=16)),
                ("visibility", models.CharField(choices=[("public", "Public"), ("private", "Private"), ("invite_only", "Invite only")], db_index=True, default="private", max_length=16)),
                ("status", models.CharField(choices=[("waiting", "Waiting"), ("ready", "Ready"), ("in_progress", "In progress"), ("finished", "Finished"), ("aborted", "Aborted"), ("expired", "Expired")], db_index=True, default="waiting", max_length=16)),
                ("rated", models.BooleanField(default=False)),
                ("allow_guests", models.BooleanField(default=True)),
                ("spectator_enabled", models.BooleanField(default=True)),
                ("max_players", models.PositiveSmallIntegerField(default=2)),
                ("time_category", models.CharField(choices=[("bullet", "Bullet"), ("blitz", "Blitz"), ("rapid", "Rapid"), ("classical", "Classical"), ("daily", "Daily"), ("custom", "Custom")], db_index=True, default="blitz", max_length=16)),
                ("clock_initial_seconds", models.PositiveIntegerField(default=300)),
                ("increment_seconds", models.PositiveSmallIntegerField(default=0)),
                ("delay_seconds", models.PositiveSmallIntegerField(default=0)),
                ("color_preference", models.CharField(choices=[("random", "Random"), ("white", "White"), ("black", "Black")], default="random", max_length=10)),
                ("private_note", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("last_activity_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("host", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="hosted_rooms", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-last_activity_at", "-created_at"],
                "indexes": [
                    models.Index(fields=["code"], name="rooms_room_code_idx"),
                    models.Index(fields=["mode", "status"], name="rooms_room_mode_status_idx"),
                    models.Index(fields=["visibility", "status"], name="rooms_room_visible_status_idx"),
                    models.Index(fields=["time_category", "rated"], name="rooms_room_time_rated_idx"),
                    models.Index(fields=["last_activity_at"], name="rooms_room_last_activity_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("code",), name="rooms_room_code_unique"),
                    models.CheckConstraint(condition=Q(("max_players__gte", 2)), name="rooms_room_min_players"),
                    models.CheckConstraint(condition=Q(("clock_initial_seconds__gte", 0)), name="rooms_room_clock_nonnegative"),
                ],
            },
        ),
        migrations.CreateModel(
            name="RoomParticipant",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("guest_key", models.CharField(blank=True, db_index=True, max_length=64)),
                ("display_name", models.CharField(max_length=80)),
                ("role", models.CharField(choices=[("host", "Host"), ("player", "Player"), ("spectator", "Spectator")], db_index=True, default="player", max_length=16)),
                ("status", models.CharField(choices=[("invited", "Invited"), ("joined", "Joined"), ("ready", "Ready"), ("left", "Left"), ("kicked", "Kicked")], db_index=True, default="joined", max_length=16)),
                ("side", models.CharField(choices=[("white", "White"), ("black", "Black"), ("random", "Random"), ("none", "None")], default="random", max_length=8)),
                ("is_connected", models.BooleanField(db_index=True, default=False)),
                ("connection_count", models.PositiveSmallIntegerField(default=0)),
                ("joined_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("left_at", models.DateTimeField(blank=True, null=True)),
                ("last_seen_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="participants", to="rooms.room")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="room_participations", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["role", "joined_at"],
                "indexes": [
                    models.Index(fields=["room", "role", "status"], name="rooms_participant_role_idx"),
                    models.Index(fields=["room", "is_connected"], name="rooms_participant_presence_idx"),
                    models.Index(fields=["guest_key"], name="rooms_participant_guest_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(condition=Q(("user__isnull", False)), fields=("room", "user"), name="rooms_unique_user_per_room"),
                    models.UniqueConstraint(condition=~Q(("guest_key", "")), fields=("room", "guest_key"), name="rooms_unique_guest_per_room"),
                ],
            },
        ),
        migrations.CreateModel(
            name="RoomEvent",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(choices=[("room.created", "Room created"), ("participant.joined", "Participant joined"), ("participant.left", "Participant left"), ("participant.ready", "Participant ready"), ("chat.message", "Chat message"), ("room.updated", "Room updated"), ("error", "Error")], db_index=True, max_length=64)),
                ("actor_guest_key", models.CharField(blank=True, db_index=True, max_length=64)),
                ("actor_display_name", models.CharField(blank=True, max_length=80)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("actor_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="room_events", to=settings.AUTH_USER_MODEL)),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="rooms.room")),
            ],
            options={
                "ordering": ["created_at"],
                "indexes": [
                    models.Index(fields=["room", "event_type", "created_at"], name="rooms_event_room_type_idx"),
                    models.Index(fields=["room", "created_at"], name="rooms_event_room_time_idx"),
                ],
            },
        ),
    ]
