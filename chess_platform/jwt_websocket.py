from __future__ import annotations

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def _user_for_token(raw_token: str):
    authentication = JWTAuthentication()
    validated = authentication.get_validated_token(raw_token)
    return authentication.get_user(validated)


class JwtAuthMiddleware(BaseMiddleware):
    """Authenticate native WebSocket clients with an Authorization header."""

    async def __call__(self, scope, receive, send):
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        authorization = headers.get(b"authorization", b"").decode("utf-8")
        token = authorization[7:] if authorization.lower().startswith("bearer ") else None
        if token:
            try:
                scope["user"] = await _user_for_token(token)
            except Exception:
                scope["user"] = AnonymousUser()
        return await super().__call__(scope, receive, send)
