from __future__ import annotations

import pytest
from asgiref.sync import async_to_sync
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.games.consumers import GameConsumer
from apps.games.services import create_same_pc_game
from chess_platform.jwt_websocket import JwtAuthMiddleware, _user_for_token


@pytest.mark.django_db(transaction=True)
def test_websocket_jwt_resolves_mobile_user() -> None:
    user = User.objects.create_user(email="mobile-ws@example.com", password="StrongPass123!")
    resolved = async_to_sync(_user_for_token)(str(AccessToken.for_user(user)))
    assert resolved.pk == user.pk


@pytest.mark.django_db(transaction=True)
def test_websocket_authorization_header_sets_scope_user() -> None:
    user = User.objects.create_user(email="mobile-header@example.com", password="StrongPass123!")
    token = str(AccessToken.for_user(user))
    captured = {}

    async def application(scope, receive, send):
        captured["user_id"] = scope["user"].pk

    async def receive():
        return {"type": "websocket.disconnect"}

    async def send(_message):
        return None

    middleware = JwtAuthMiddleware(application)
    scope = {"type": "websocket", "headers": [(b"authorization", f"Bearer {token}".encode())]}
    async_to_sync(middleware)(scope, receive, send)

    assert captured["user_id"] == user.pk


@pytest.mark.django_db
def test_game_websocket_state_contains_viewer_color() -> None:
    user = User.objects.create_user(email="white-mobile@example.com", password="StrongPass123!")
    game = create_same_pc_game(white_name="Mobile", black_name="Opponent", initial_minutes=5)
    game.metadata = {"mode": "online"}
    game.white_user = user
    game.save(update_fields=["metadata", "white_user", "updated_at"])

    consumer = GameConsumer()
    consumer.scope = {"user": user}
    payload = consumer._serialized_for_viewer(game)

    assert payload["viewer"] == {"color": "white", "name": user.display_name, "can_move": True}
