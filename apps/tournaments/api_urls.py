from django.urls import path

from .api_views import CompetitionHubAPIView, TournamentAPIView

urlpatterns = [
    path("tournaments/", TournamentAPIView.as_view()),
    path("tournaments/<int:pk>/", TournamentAPIView.as_view()),
    path("competitions/", CompetitionHubAPIView.as_view()),
]
