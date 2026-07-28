from __future__ import annotations

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(db_index=True, max_length=254, unique=True, verbose_name="email address")),
                ("first_name", models.CharField(blank=True, max_length=150)),
                ("last_name", models.CharField(blank=True, max_length=150)),
                ("display_name", models.CharField(blank=True, db_index=True, max_length=80)),
                ("bio", models.TextField(blank=True)),
                ("avatar", models.ImageField(blank=True, null=True, upload_to="avatars/%Y/%m/")),
                ("country", models.CharField(blank=True, max_length=2)),
                ("time_zone", models.CharField(default="Asia/Kolkata", max_length=64)),
                ("is_email_verified", models.BooleanField(default=False)),
                ("two_factor_enabled", models.BooleanField(default=False)),
                ("totp_secret", models.CharField(blank=True, max_length=64)),
                ("is_staff", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "ordering": ["-date_joined"],
                "indexes": [
                    models.Index(fields=["email"], name="accounts_user_email_idx"),
                    models.Index(fields=["display_name"], name="accounts_user_display_idx"),
                    models.Index(fields=["last_seen_at"], name="accounts_user_lastseen_idx"),
                ],
                "constraints": [models.UniqueConstraint(fields=("email",), name="accounts_user_email_unique")],
            },
        ),
        migrations.CreateModel(
            name="EmailOTP",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "purpose",
                    models.CharField(
                        choices=[
                            ("verify_email", "Verify email"),
                            ("login", "Login"),
                            ("password_reset", "Password reset"),
                        ],
                        max_length=32,
                    ),
                ),
                ("code_hash", models.CharField(max_length=256)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("used_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=255)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_otps",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["user", "purpose", "used_at"], name="emailotp_user_purpose_idx"),
                    models.Index(fields=["expires_at"], name="emailotp_expires_idx"),
                ],
            },
        ),
    ]
