from chess_platform.routing import websocket_urlpatterns
from django.conf import settings
from django.urls import resolve, reverse

from apps.accounts.models import User


def test_api_schema_is_available(client):
    response = client.get(reverse("schema"))

    assert response.status_code == 200
    assert settings.REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] == "drf_spectacular.openapi.AutoSchema"


def test_responses_include_request_trace_and_server_timing(client):
    response = client.get(reverse("core:health"), HTTP_X_REQUEST_ID="device-test-1")

    assert response.headers["X-Request-ID"] == "device-test-1"
    assert response.headers["Server-Timing"].startswith("app;dur=")
    assert set(response.json()["timings"]) == {
        "database_ms",
        "cache_ms",
        "total_ms",
    }

    sanitized = client.get(reverse("core:health"), HTTP_X_REQUEST_ID="bad value")
    assert sanitized.headers["X-Request-ID"] != "bad value"
    assert len(sanitized.headers["X-Request-ID"]) == 32


def test_analysis_and_stockfish_routes_are_registered():
    assert resolve("/analysis/board/").view_name == "analysis:board"
    assert resolve("/stockfish/status/").view_name == "stockfish:status"


def test_expected_websocket_routes_are_registered():
    route_patterns = {str(route.pattern) for route in websocket_urlpatterns}

    assert "ws/ping/" in route_patterns
    assert "ws/rooms/<str:code>/" in route_patterns
    assert "ws/games/<uuid:game_id>/" in route_patterns


def test_home_displays_mobile_style_quick_play(client, db):
    response = client.get(reverse("core:home"))

    assert response.status_code == 200
    assert b"Choose a mode" in response.content
    assert b"Play with Bot" in response.content
    assert b"Play Online" in response.content
    assert b"fonts.googleapis.com" not in response.content
    assert b"Dashboard" not in response.content
    assert b"Matchmaking" not in response.content


def test_signed_in_header_shows_player_navigation_without_guest_actions(client, db):
    user = User.objects.create_user(
        email="navigation@example.com",
        password="StrongPass123!",
        display_name="Navigator",
        is_email_verified=True,
    )
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    response = client.get(reverse("core:play"))

    assert response.status_code == 200
    assert b"Dashboard" in response.content
    assert b"Matchmaking" in response.content
    assert b"My profile" in response.content
    assert b">Login<" not in response.content
    assert b"Create Account" not in response.content


def test_signed_in_home_has_progress_and_live_activity(client, db):
    user = User.objects.create_user(email="progress@example.com", password="StrongPass123!", display_name="Progress")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    response = client.get(reverse("core:play"))

    assert response.status_code == 200
    assert len(response.context["achievements"]) == 4
    assert len(response.context["daily_goals"]) == 3
    assert response.context["active_game_count"] >= 0
    assert b"Build your chess story" in response.content
    assert b"The club is active" in response.content


def test_signed_in_home_redirects_to_dashboard_and_play_hides_marketing(client, db):
    user = User.objects.create_user(email="member@example.com", password="StrongPass123!", display_name="Member")
    client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")

    response = client.get(reverse("core:home"))
    assert response.status_code == 302
    assert response.url == reverse("dashboard:home")

    play = client.get(reverse("core:play"))
    assert play.status_code == 200
    assert b"Start your next game" in play.content
    assert b"Chess for every" not in play.content


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
