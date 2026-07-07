from apps.games.routing import websocket_urlpatterns as games_websocket_urlpatterns

websocket_urlpatterns = [
    *games_websocket_urlpatterns,
]