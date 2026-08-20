from django.urls import path

from .api_views import (
    LeaderboardAPIView,
    MeAPIView,
    MobileBotVictoryAPIView,
    MobileExperienceAPIView,
    MobileRegisterAPIView,
    MobileVerifyEmailAPIView,
    PlayerComparisonAPIView,
    PublicProfileAPIView,
    PuzzleListAPIView,
    PuzzlePlayAPIView,
)

app_name = "accounts_api"
urlpatterns = [
    path("me/", MeAPIView.as_view(), name="me"),
    path("register/", MobileRegisterAPIView.as_view(), name="register"),
    path("verify-email/", MobileVerifyEmailAPIView.as_view(), name="verify-email"),
    path("bot-victory/", MobileBotVictoryAPIView.as_view(), name="bot-victory"),
    path("leaderboard/", LeaderboardAPIView.as_view(), name="leaderboard"),
    path("experience/", MobileExperienceAPIView.as_view(), name="experience"),
    path("players/<uuid:pk>/compare/", PlayerComparisonAPIView.as_view(), name="player-comparison"),
    path("players/<uuid:pk>/", PublicProfileAPIView.as_view(), name="public-profile"),
    path("puzzles/", PuzzleListAPIView.as_view(), name="puzzles"),
    path("puzzles/<int:pk>/play/", PuzzlePlayAPIView.as_view(), name="puzzle-play"),
]
