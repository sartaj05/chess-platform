from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import Mission, NewsArticle, PlayerReward
from apps.core.retention import (
    claim_mission,
    create_achievement_share,
    create_referral_invite,
    mission_dashboard,
    redeem_referral,
)
from apps.games.models import Game


@pytest.mark.django_db
def test_daily_mission_claim_and_achievement_share():
    user = User.objects.create_user(email="missions@example.com")
    Game.objects.create(
        white_user=user, white_display_name=user.display_name, black_display_name="Bot",
        status=Game.Status.FINISHED, result=Game.Result.WHITE_WIN,
    )
    mission = Mission.objects.create(
        title="Play today", description="Complete one game", period=Mission.Period.DAILY,
        metric=Mission.Metric.GAMES, target=1, reward_points=40,
    )
    dashboard = mission_dashboard(user)
    assert next(row for row in dashboard if row["id"] == mission.pk)["completed"] is True
    reward = claim_mission(user, mission.pk)
    assert reward.points == 40
    share = create_achievement_share(user, "first_move")
    assert share.title == "First Move"


@pytest.mark.django_db
def test_referral_reward_can_only_be_redeemed_once_per_account():
    inviter = User.objects.create_user(email="inviter@example.com")
    newcomer = User.objects.create_user(email="newcomer@example.com")
    invite = create_referral_invite(inviter)
    redeem_referral(invite.code, newcomer)
    assert PlayerReward.objects.get(user=inviter).points == 100
    with pytest.raises(ValueError, match="already redeemed"):
        redeem_referral(invite.code, newcomer)


@pytest.mark.django_db
def test_retention_feed_and_presence_heartbeat(client):
    user = User.objects.create_user(email="feed@example.com", password="test-pass-123")
    NewsArticle.objects.create(
        title="Summer arena", summary="Seasonal event starts soon", body="Details",
        is_published=True, published_at=timezone.now() - timedelta(minutes=1),
    )
    client.force_login(user)
    feed = client.get(reverse("api:retention-hub"))
    assert feed.status_code == 200
    assert feed.json()["news"][0]["title"] == "Summer arena"
    heartbeat = client.post(reverse("api:presence-heartbeat"))
    assert heartbeat.status_code == 200
    assert cache.get(f"presence:user:{user.pk}") is True
