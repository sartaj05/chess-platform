from django.urls import path

from apps.games.views import (
    AbortGameView,
    DeclineDrawView,
    DrawOfferView,
    FenDownloadView,
    FenImportView,
    GamePlayView,
    GameStateView,
    PgnDownloadView,
    ResignGameView,
    SamePcGameCreateView,
    StartRoomGameView,
)

app_name = "games"

urlpatterns = [
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
