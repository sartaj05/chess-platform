from __future__ import annotations

import secrets
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.games.models import Game, GameMove
from apps.puzzles.models import PuzzleAttempt
from apps.tournaments.models import Club, TeamBoard

from .models import AchievementShare, Mission, PlayerReward, Referral, ReferralInvite, UserMission
from .product_experience import player_progress


def mission_period(mission: Mission):
    today = timezone.localdate()
    if mission.period == Mission.Period.WEEKLY:
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=7), start.isoformat()
    return today, today + timedelta(days=1), today.isoformat()


def metric_progress(user: User, mission: Mission, start, end) -> int:
    games = Game.objects.filter(Q(white_user=user) | Q(black_user=user), created_at__date__gte=start,
                                created_at__date__lt=end)
    if mission.metric == Mission.Metric.GAMES:
        return games.count()
    if mission.metric == Mission.Metric.WINS:
        return games.filter(Q(white_user=user, result=Game.Result.WHITE_WIN) |
                            Q(black_user=user, result=Game.Result.BLACK_WIN)).count()
    if mission.metric == Mission.Metric.PUZZLES:
        return PuzzleAttempt.objects.filter(user=user, solved_at__date__gte=start,
                                            solved_at__date__lt=end,
                                            status=PuzzleAttempt.Status.SOLVED).count()
    return GameMove.objects.filter(played_by_user=user, created_at__date__gte=start,
                                   created_at__date__lt=end).count()


def mission_dashboard(user: User) -> list[dict]:
    rows = []
    for mission in Mission.objects.filter(is_active=True).order_by("period", "title"):
        start, end, key = mission_period(mission)
        progress = metric_progress(user, mission, start, end)
        record, _ = UserMission.objects.get_or_create(user=user, mission=mission, period_key=key)
        complete = progress >= mission.target
        updates = []
        if record.progress != progress:
            record.progress = progress
            updates.append("progress")
        if complete and record.completed_at is None:
            record.completed_at = timezone.now()
            updates.append("completed_at")
        if updates:
            record.save(update_fields=[*updates, "updated_at"])
        rows.append({"id": mission.pk, "title": mission.title, "description": mission.description,
                     "period": mission.period, "progress": min(progress, mission.target),
                     "target": mission.target, "reward_points": mission.reward_points,
                     "completed": complete, "claimed": record.claimed_at is not None})
    return rows


def claim_mission(user: User, mission_id: int) -> PlayerReward:
    mission = Mission.objects.get(pk=mission_id, is_active=True)
    _start, _end, key = mission_period(mission)
    record = UserMission.objects.get(user=user, mission=mission, period_key=key)
    if record.completed_at is None or record.claimed_at is not None:
        raise ValueError("This mission reward is not available.")
    record.claimed_at = timezone.now()
    record.save(update_fields=["claimed_at", "updated_at"])
    rewards, _ = PlayerReward.objects.get_or_create(user=user)
    rewards.points += mission.reward_points
    rewards.save(update_fields=["points", "updated_at"])
    return rewards


def create_achievement_share(user: User, key: str) -> AchievementShare:
    key = key.replace("-", "_").lower()
    achievement = next((item for item in player_progress(user)["achievements"]
                        if item["name"].lower().replace(" ", "_") == key and item["unlocked"]), None)
    if achievement is None:
        raise ValueError("Unlock this achievement before sharing it.")
    return AchievementShare.objects.create(
        user=user, achievement_key=key, title=achievement["name"],
        share_code=secrets.token_urlsafe(10)[:16], payload=achievement,
    )


def create_referral_invite(inviter: User) -> ReferralInvite:
    return ReferralInvite.objects.create(inviter=inviter, code=ReferralInvite.new_code())


def redeem_referral(code: str, referred_user: User) -> Referral:
    if Referral.objects.filter(referred_user=referred_user).exists():
        raise ValueError("This account has already redeemed a referral.")
    invite = ReferralInvite.objects.select_related("inviter").get(code=code.strip().upper())
    if invite.inviter_id == referred_user.pk or invite.uses >= invite.max_uses:
        raise ValueError("This referral code cannot be redeemed.")
    referral = Referral.objects.create(inviter=invite.inviter, referred_user=referred_user, invite=invite,
                                       rewarded_at=timezone.now())
    invite.uses += 1
    invite.save(update_fields=["uses", "updated_at"])
    inviter = invite.inviter
    reward, _ = PlayerReward.objects.get_or_create(user=inviter)
    reward.points += 100
    reward.referrals += 1
    reward.save(update_fields=["points", "referrals", "updated_at"])
    return referral


def club_leaderboard() -> list[dict]:
    rows = []
    for club in Club.objects.prefetch_related("members").all():
        members = list(club.members.all())
        member_ids = {user.pk for user in members}
        board_wins = 0
        boards = TeamBoard.objects.filter(Q(home_club=club) | Q(away_club=club)).select_related("game")
        for board in boards:
            winner_id = (board.game.white_user_id if board.game.result == Game.Result.WHITE_WIN
                         else board.game.black_user_id if board.game.result == Game.Result.BLACK_WIN else None)
            if winner_id in member_ids:
                board_wins += 1
        rating = round(sum(user.rating for user in members) / len(members)) if members else 0
        rows.append({"id": club.pk, "name": club.name, "members": len(members),
                     "average_rating": rating, "league_wins": board_wins,
                     "score": board_wins * 100 + rating})
    return sorted(rows, key=lambda row: row["score"], reverse=True)
