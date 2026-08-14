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


def test_home_displays_mobile_style_quick_play(client):
    response = client.get(reverse("core:home"))

    assert response.status_code == 200
    assert b"Choose a mode" in response.content
    assert b"Play with Bot" in response.content
    assert b"Play Online" in response.content


def test_home_can_start_same_pc_game(client, db):
    response = client.post(
        reverse("core:home"),
        {"action": "same_pc", "display_name": "Alice", "side": "black"},
    )

    assert response.status_code == 302
    from apps.games.models import Game

    game = Game.objects.latest("created_at")
    assert game.white_display_name == "Friend"
    assert game.black_display_name == "Alice"


def test_home_bot_plays_first_when_player_selects_black(client, db):
    response = client.post(
        reverse("core:home"),
        {"action": "bot", "display_name": "Alice", "side": "black"},
    )

    assert response.status_code == 302
    from apps.games.models import Game

    game = Game.objects.latest("created_at")
    assert game.metadata["mode"] == "local_ai"
    assert game.metadata["player_color"] == "black"
    assert game.metadata["bot_level"] == 1
    assert game.metadata["bot_engine"] in {"stockfish", "built_in_fallback"}
    assert game.white_display_name == "Bot"
    assert game.ply_count == 1
    assert game.turn == "black"
