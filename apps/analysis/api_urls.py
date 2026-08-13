from django.urls import path

from apps.analysis.api_views import (
    GameAnalysisJobApiView,
    OpeningExplorerApiView,
    PositionAnalysisApiView,
    PersonalOpeningStatsApiView,
    StartGameAnalysisApiView,
)

urlpatterns = [
    path("analysis/games/<uuid:pk>/start/", StartGameAnalysisApiView.as_view(), name="analysis-game-start"),
    path("analysis/jobs/<uuid:pk>/", GameAnalysisJobApiView.as_view(), name="analysis-job-detail"),
    path("analysis/position/", PositionAnalysisApiView.as_view(), name="analysis-position"),
    path("analysis/openings/", OpeningExplorerApiView.as_view(), name="analysis-openings"),
    path("analysis/openings/personal/", PersonalOpeningStatsApiView.as_view(), name="analysis-opening-stats"),
]
