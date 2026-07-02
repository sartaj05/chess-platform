from django.urls import path

from apps.analysis.views import AnalysisBoardView, AnalysisJobDetailView, AnalysisJobStateView, GameReviewView, OpeningExplorerJsonView, OpeningExplorerView, StartGameAnalysisView

app_name = "analysis"

urlpatterns = [
    path("analysis/board/", AnalysisBoardView.as_view(), name="board"),
    path("analysis/openings/", OpeningExplorerView.as_view(), name="opening_explorer"),
    path("analysis/openings.json", OpeningExplorerJsonView.as_view(), name="opening_explorer_json"),
    path("analysis/jobs/<uuid:pk>/", AnalysisJobDetailView.as_view(), name="job_detail"),
    path("analysis/jobs/<uuid:pk>/state/", AnalysisJobStateView.as_view(), name="job_state"),
    path("games/<uuid:pk>/review/", GameReviewView.as_view(), name="game_review"),
    path("games/<uuid:pk>/review/start/", StartGameAnalysisView.as_view(), name="start_game_review"),
]
