from __future__ import annotations

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chess_platform.settings.dev")

django_asgi_app = get_asgi_application()

from chess_platform.jwt_websocket import JwtAuthMiddleware  # noqa: E402
from chess_platform.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(JwtAuthMiddleware(URLRouter(websocket_urlpatterns))),
    }
)
