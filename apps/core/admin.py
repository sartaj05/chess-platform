from django.contrib import admin

from .models import AchievementShare, Mission, NewsArticle, PlayerReward, Referral, ReferralInvite, Season, UserMission

admin.site.register(Season)
admin.site.register(Mission)
admin.site.register(UserMission)
admin.site.register(PlayerReward)
admin.site.register(ReferralInvite)
admin.site.register(Referral)
admin.site.register(AchievementShare)
admin.site.register(NewsArticle)
