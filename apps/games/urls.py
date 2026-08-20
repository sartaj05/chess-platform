from django.urls import path

from apps.games.views import (
    AbortGameView,
    DeclineDrawView,
    DrawOfferView,
    FairPlayAppealCreateView,
    FairPlayAppealResolveView,
    FenDownloadView,
    FenImportView,
    GamePlayView,
    GameStateView,
    ModeratorDashboardView,
    ModeratorReviewView,
    PgnDownloadView,
    ResignGameView,
    SamePcGameCreateView,
    StartRoomGameView,
)

app_name = "games"

urlpatterns = [
    path("moderation/", ModeratorDashboardView.as_view(), name="moderator_dashboard"),
    path("moderation/reviews/<int:pk>/", ModeratorReviewView.as_view(), name="moderator_review"),
    path("moderation/appeals/<int:pk>/", FairPlayAppealResolveView.as_view(), name="appeal_resolve"),
    path("fair-play/<int:pk>/appeal/", FairPlayAppealCreateView.as_view(), name="appeal_create"),
    path("games/same-pc/new/", SamePcGameCreateView.as_view(), name="same_pc_new"),
    path("games/fen/import/", FenImportView.as_view(), name="fen_import"),
    path("games/<uuid:pk>/", GamePlayView.as_view(), name="play"),
    path("games/<uuid:pk>/state/", GameStateView.as_view(), name="state"),
    path("games/<uuid:pk>/fen/", FenDownloadView.as_view(), name="fen"),
    path("games/<uuid:pk>/pgn/", PgnDownloadView.as_view(), name="pgn"),
    path("games/<uuid:pk>/resign/", ResignGameView.as_view(), name="resign"),
    path("games/<uuid:pk>/abort/", AbortGameView.as_view(), name="abort"),
    path("games/<uuid:pk>/draw/", DrawOfferView.as_view(), name="draw"),
    path("games/<uuid:pk>/draw/decline/", DeclineDrawView.as_view(), name="decline_draw"),
    path("play/<str:code>/start-game/", StartRoomGameView.as_view(), name="start_room_game"),
]
