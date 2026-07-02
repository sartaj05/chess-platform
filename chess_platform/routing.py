from __future__ import annotations

from apps.core.routing import websocket_urlpatterns as core_websocket_urlpatterns
from apps.rooms.routing import websocket_urlpatterns as room_websocket_urlpatterns
from apps.games.routing import websocket_urlpatterns as game_websocket_urlpatterns

websocket_urlpatterns = [*core_websocket_urlpatterns, *room_websocket_urlpatterns, *game_websocket_urlpatterns]
