from django.urls import path

from apps.rooms.api_views import JoinRoomAPIView, MatchmakingAPIView, RoomListCreateAPIView, RoomRetrieveAPIView, StartRoomGameAPIView

app_name = "rooms-api"

urlpatterns = [
    path("rooms/", RoomListCreateAPIView.as_view(), name="room-list-create"),
    path("matchmaking/", MatchmakingAPIView.as_view(), name="matchmaking"),
    path("rooms/<str:code>/", RoomRetrieveAPIView.as_view(), name="room-detail"),
    path("rooms/<str:code>/join/", JoinRoomAPIView.as_view(), name="room-join"),
    path("rooms/<str:code>/start/", StartRoomGameAPIView.as_view(), name="room-start"),
]
