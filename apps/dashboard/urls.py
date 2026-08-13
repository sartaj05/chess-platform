from django.urls import path

from .views import DashboardView, LeaderboardView

app_name = "dashboard"
urlpatterns = [path("", DashboardView.as_view(), name="home"), path("leaderboard/", LeaderboardView.as_view(), name="leaderboard")]
