from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework import permissions, response, views

from apps.friends.models import FriendChallenge
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.tournaments.models import TournamentAnnouncement

from .models import NewsArticle, PlayerReward, ReferralInvite, Season
from .product_experience import player_progress
from .retention import (
    claim_mission,
    club_leaderboard,
    create_achievement_share,
    create_referral_invite,
    mission_dashboard,
    redeem_referral,
)


class RetentionHubAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rewards, _ = PlayerReward.objects.get_or_create(user=request.user)
        season = Season.objects.filter(is_active=True, starts_at__lte=timezone.now(), ends_at__gte=timezone.now()).first()
        news = list(NewsArticle.objects.filter(is_published=True, published_at__lte=timezone.now())[:20])
        announcements = TournamentAnnouncement.objects.filter(
            tournament__entries__user=request.user
        ).select_related("tournament", "author")[:20]
        return response.Response({
            "points": rewards.points,
            "referrals": rewards.referrals,
            "season": None if season is None else {"name": season.name, "theme": season.theme,
                                                    "ends_at": season.ends_at,
                                                    "reward_title": season.reward_title},
            "missions": mission_dashboard(request.user),
            "achievements": player_progress(request.user)["achievements"],
            "club_leaderboard": club_leaderboard()[:50],
            "news": [
                {"kind": "news", "id": item.pk, "title": item.title, "summary": item.summary,
                 "published_at": item.published_at} for item in news
            ] + [
                {"kind": "tournament", "id": item.pk, "title": item.tournament.name,
                 "summary": item.body, "published_at": item.created_at,
                 "url": item.tournament.get_absolute_url()} for item in announcements
            ],
            "referral_codes": list(ReferralInvite.objects.filter(inviter=request.user).values("code", "uses", "max_uses")),
        })

    def post(self, request):
        action = request.data.get("action", "")
        try:
            if action == "claim_mission":
                reward = claim_mission(request.user, int(request.data.get("mission_id")))
                return response.Response({"points": reward.points})
            if action == "share_achievement":
                share = create_achievement_share(request.user, request.data.get("achievement_key", ""))
                return response.Response({"share_code": share.share_code,
                                          "share_url": f"/achievements/{share.share_code}/"}, status=201)
            if action == "create_referral":
                invite = create_referral_invite(request.user)
                return response.Response({"code": invite.code, "reward_points": 100}, status=201)
            if action == "redeem_referral":
                referral = redeem_referral(request.data.get("code", ""), request.user)
                return response.Response({"inviter": referral.inviter.display_name, "rewarded": True})
            if action == "challenge_reminder":
                challenge = FriendChallenge.objects.select_related("challenged", "room").get(
                    pk=request.data.get("challenge_id"), challenger=request.user, status="pending"
                )
                if challenge.reminded_at and challenge.reminded_at > timezone.now() - timedelta(hours=24):
                    raise ValueError("A reminder was already sent in the last 24 hours.")
                notify(recipient=challenge.challenged, kind=Notification.Kind.SYSTEM,
                       title=f"Reminder: {request.user.display_name} is waiting to play",
                       target_url=challenge.room.get_absolute_url() if challenge.room else "")
                challenge.reminded_at = timezone.now()
                challenge.save(update_fields=["reminded_at", "updated_at"])
                return response.Response({"reminded": True})
        except (ValueError, FriendChallenge.DoesNotExist, ReferralInvite.DoesNotExist) as exc:
            return response.Response({"detail": str(exc)}, status=400)
        return response.Response({"detail": "Unsupported retention action."}, status=400)


class PresenceAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cache.set(f"presence:user:{request.user.pk}", True, 90)
        request.user.last_seen_at = timezone.now()
        request.user.save(update_fields=["last_seen_at"])
        return response.Response({"online": True, "last_seen_at": request.user.last_seen_at})
