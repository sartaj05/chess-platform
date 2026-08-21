from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Season(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=False, db_index=True)
    theme = models.CharField(max_length=40, default="classic")
    reward_title = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self) -> str:
        return self.name


class Mission(TimeStampedModel):
    class Period(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"

    class Metric(models.TextChoices):
        GAMES = "games", "Games played"
        WINS = "wins", "Games won"
        PUZZLES = "puzzles", "Puzzles solved"
        MOVES = "moves", "Moves played"

    title = models.CharField(max_length=120)
    description = models.CharField(max_length=240)
    period = models.CharField(max_length=10, choices=Period.choices)
    metric = models.CharField(max_length=12, choices=Metric.choices)
    target = models.PositiveIntegerField(default=1)
    reward_points = models.PositiveIntegerField(default=25)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self) -> str:
        return self.title


class UserMission(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mission_progress")
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name="progress_records")
    period_key = models.CharField(max_length=16)
    progress = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "mission", "period_key"], name="mission_user_period")]

    def __str__(self) -> str:
        return f"{self.user}: {self.mission} ({self.period_key})"


class PlayerReward(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rewards")
    points = models.PositiveIntegerField(default=0)
    referrals = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.user}: {self.points} points"


class ReferralInvite(TimeStampedModel):
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_invites")
    code = models.CharField(max_length=12, unique=True, db_index=True)
    uses = models.PositiveIntegerField(default=0)
    max_uses = models.PositiveIntegerField(default=25)

    def __str__(self) -> str:
        return self.code

    @classmethod
    def new_code(cls) -> str:
        while True:
            code = secrets.token_urlsafe(8).upper()[:12]
            if not cls.objects.filter(code=code).exists():
                return code

class Referral(TimeStampedModel):
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referrals_sent")
    referred_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral")
    invite = models.ForeignKey(ReferralInvite, on_delete=models.CASCADE, related_name="redemptions")
    rewarded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.inviter} invited {self.referred_user}"


class AchievementShare(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="achievement_shares")
    achievement_key = models.CharField(max_length=64)
    title = models.CharField(max_length=120)
    share_code = models.CharField(max_length=16, unique=True, db_index=True)
    payload = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"{self.user}: {self.title}"


class NewsArticle(TimeStampedModel):
    class Audience(models.TextChoices):
        ALL = "all", "Everyone"
        MEMBERS = "members", "Signed-in players"

    title = models.CharField(max_length=160)
    summary = models.CharField(max_length=300)
    body = models.TextField()
    audience = models.CharField(max_length=12, choices=Audience.choices, default=Audience.ALL)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)

    def __str__(self) -> str:
        return self.title
