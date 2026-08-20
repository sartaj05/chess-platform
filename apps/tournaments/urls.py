from django.urls import path

from .views import (
    CancelTournamentView,
    CompetitionHubView,
    JoinTournamentView,
    RemoveTournamentPlayerView,
    ReportPairingResultView,
    StartTournamentView,
    TournamentAnnouncementView,
    TournamentChatView,
    TournamentCreateView,
    TournamentDetailView,
    TournamentInviteView,
    TournamentListView,
    WithdrawTournamentView,
)

app_name = "tournaments"
urlpatterns = [
    path("", TournamentListView.as_view(), name="list"),
    path("create/", TournamentCreateView.as_view(), name="create"),
    path("competitions/", CompetitionHubView.as_view(), name="competition_hub"),
    path("join-code/", TournamentInviteView.as_view(), name="join_code"),
    path("<int:pk>/", TournamentDetailView.as_view(), name="detail"),
    path("<int:pk>/join/", JoinTournamentView.as_view(), name="join"),
    path("<int:pk>/withdraw/", WithdrawTournamentView.as_view(), name="withdraw"),
    path("<int:pk>/start/", StartTournamentView.as_view(), name="start"),
    path("<int:pk>/pairings/<int:pairing_pk>/result/", ReportPairingResultView.as_view(), name="report_result"),
    path("<int:pk>/cancel/", CancelTournamentView.as_view(), name="cancel"),
    path("<int:pk>/players/<int:entry_pk>/remove/", RemoveTournamentPlayerView.as_view(), name="remove_player"),
    path("<int:pk>/announce/", TournamentAnnouncementView.as_view(), name="announce"),
    path("<int:pk>/chat/", TournamentChatView.as_view(), name="chat"),
]
