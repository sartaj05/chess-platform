from apps.games.routing import websocket_urlpatterns as games_websocket_urlpatterns
from apps.rooms.routing import websocket_urlpatterns as rooms_websocket_urlpatterns

websocket_urlpatterns = [
    *rooms_websocket_urlpatterns,
    *games_websocket_urlpatterns,
]
