from django.urls import path

from .views import (
    JoinTournamentView,
    ReportPairingResultView,
    StartTournamentView,
    TournamentCreateView,
    TournamentDetailView,
    TournamentListView,
    WithdrawTournamentView,
)

app_name = "tournaments"
urlpatterns = [
    path("", TournamentListView.as_view(), name="list"),
    path("create/", TournamentCreateView.as_view(), name="create"),
    path("<int:pk>/", TournamentDetailView.as_view(), name="detail"),
    path("<int:pk>/join/", JoinTournamentView.as_view(), name="join"),
    path("<int:pk>/withdraw/", WithdrawTournamentView.as_view(), name="withdraw"),
    path("<int:pk>/start/", StartTournamentView.as_view(), name="start"),
    path("<int:pk>/pairings/<int:pairing_pk>/result/", ReportPairingResultView.as_view(), name="report_result"),
]
