from __future__ import annotations

import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.managers import UserManager
from apps.core.models import TimeStampedModel


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    display_name = models.CharField(max_length=80, blank=True, db_index=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", blank=True, null=True)
    country = models.CharField(max_length=2, blank=True)
    time_zone = models.CharField(max_length=64, default="Asia/Kolkata")
    is_email_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    totp_secret = models.CharField(max_length=64, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(blank=True, null=True, db_index=True)
    bot_level = models.PositiveSmallIntegerField(default=1)
    rating = models.PositiveIntegerField(default=1200, db_index=True)
    peak_rating = models.PositiveIntegerField(default=1200)
    rated_games = models.PositiveIntegerField(default=0)
    bullet_rating = models.PositiveIntegerField(default=1200, db_index=True)
    blitz_rating = models.PositiveIntegerField(default=1200, db_index=True)
    rapid_rating = models.PositiveIntegerField(default=1200, db_index=True)
    bullet_games = models.PositiveIntegerField(default=0)
    blitz_games = models.PositiveIntegerField(default=0)
    rapid_games = models.PositiveIntegerField(default=0)
    puzzle_rating = models.PositiveIntegerField(default=1200, db_index=True)
    puzzle_streak = models.PositiveIntegerField(default=0)
    puzzle_best_streak = models.PositiveIntegerField(default=0)
    last_puzzle_date = models.DateField(null=True, blank=True)
    objects = UserManager()
    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email"], name="accounts_user_email_idx"),
            models.Index(fields=["display_name"], name="accounts_user_display_idx"),
            models.Index(fields=["last_seen_at"], name="accounts_user_lastseen_idx"),
        ]
        constraints = [models.UniqueConstraint(fields=["email"], name="accounts_user_email_unique")]

    def __str__(self) -> str:
        return self.display_name or self.email

    @property
    def full_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.display_name or self.email

    def save(self, *args, **kwargs) -> None:
        if self.email:
            self.email = self.email.lower().strip()
        if not self.display_name and self.email:
            self.display_name = self.email.split("@")[0]
        if (
            self._state.adding
            and self.rating != 1200
            and self.bullet_rating == self.blitz_rating == self.rapid_rating == 1200
        ):
            self.bullet_rating = self.blitz_rating = self.rapid_rating = self.rating
        super().save(*args, **kwargs)

    def ensure_totp_secret(self) -> str:
        if not self.totp_secret:
            self.totp_secret = secrets.token_hex(20)
            self.save(update_fields=["totp_secret"])
        return self.totp_secret


class EmailOTP(TimeStampedModel):
    class Purpose(models.TextChoices):
        VERIFY_EMAIL = "verify_email", "Verify email"
        LOGIN = "login", "Login"
        PASSWORD_RESET = "password_reset", "Password reset"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_otps")
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    code_hash = models.CharField(max_length=256)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(blank=True, null=True, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "purpose", "used_at"], name="emailotp_user_purpose_idx"),
            models.Index(fields=["expires_at"], name="emailotp_expires_idx"),
        ]

    @classmethod
    def create_code(
        cls, *, user: User, purpose: str, ip_address: str | None = None, user_agent: str = ""
    ) -> tuple[EmailOTP, str]:
        raw_code = f"{secrets.randbelow(1_000_000):06d}"
        ttl = getattr(settings, "OTP_CODE_TTL_MINUTES", 10)
        otp = cls.objects.create(
            user=user,
            purpose=purpose,
            code_hash=make_password(raw_code),
            expires_at=timezone.now() + timedelta(minutes=ttl),
            ip_address=ip_address,
            user_agent=user_agent[:255],
        )
        return otp, raw_code

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def verify(self, code: str) -> bool:
        if self.is_used or self.is_expired or self.attempts >= getattr(settings, "MAX_OTP_ATTEMPTS", 5):
            return False
        self.attempts += 1
        self.save(update_fields=["attempts", "updated_at"])
        if check_password(code, self.code_hash):
            self.used_at = timezone.now()
            self.save(update_fields=["used_at", "updated_at"])
            return True
        return False


class UserPreference(TimeStampedModel):
    class ProfileVisibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PLAYERS = "players", "Signed-in players"
        PRIVATE = "private", "Private"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preferences")
    profile_visibility = models.CharField(
        max_length=12, choices=ProfileVisibility.choices, default=ProfileVisibility.PUBLIC
    )
    show_online_status = models.BooleanField(default=True)
    allow_friend_requests = models.BooleanField(default=True)
    allow_direct_messages = models.BooleanField(default=True)
    allow_challenges = models.BooleanField(default=True)
    notify_friend_activity = models.BooleanField(default=True)
    notify_messages = models.BooleanField(default=True)
    notify_tournaments = models.BooleanField(default=True)
    notify_system = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Preferences for {self.user}"
