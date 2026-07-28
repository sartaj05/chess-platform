from chess_platform.routing import websocket_urlpatterns
from django.conf import settings
from django.urls import resolve, reverse


def test_api_schema_is_available(client):
    response = client.get(reverse("schema"))

    assert response.status_code == 200
    assert settings.REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] == "drf_spectacular.openapi.AutoSchema"


def test_analysis_and_stockfish_routes_are_registered():
    assert resolve("/analysis/board/").view_name == "analysis:board"
    assert resolve("/stockfish/status/").view_name == "stockfish:status"


def test_expected_websocket_routes_are_registered():
    route_patterns = {str(route.pattern) for route in websocket_urlpatterns}

    assert "ws/ping/" in route_patterns
    assert "ws/rooms/<str:code>/" in route_patterns
    assert "ws/games/<uuid:game_id>/" in route_patterns
