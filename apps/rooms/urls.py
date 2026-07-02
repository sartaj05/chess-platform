from django.urls import path

from apps.rooms.views import CreateRoomView, JoinRoomByCodeView, LanModeView, LeaveRoomView, RoomDetailView, RoomListView, RoomStateView

app_name = "rooms"

urlpatterns = [
    path("rooms/", RoomListView.as_view(), name="list"),
    path("rooms/create/", CreateRoomView.as_view(), name="create"),
    path("rooms/join/", JoinRoomByCodeView.as_view(), name="join"),
    path("rooms/lan/", LanModeView.as_view(), name="lan_mode"),
    path("play/<str:code>/", RoomDetailView.as_view(), name="detail"),
    path("play/<str:code>/state/", RoomStateView.as_view(), name="state"),
    path("play/<str:code>/leave/", LeaveRoomView.as_view(), name="leave"),
]
