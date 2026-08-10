from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("friends/", include("apps.friends.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("chat/", include("apps.chat.urls")),
    path("puzzles/", include("apps.puzzles.urls")),
    path("tournaments/", include("apps.tournaments.urls")),
    path("", include("apps.rooms.urls")),
    path("", include("apps.games.urls")),
    path("", include("apps.analysis.urls")),
    path("", include("apps.stockfish.urls")),
    path("social/", include("allauth.urls")),
    path("api/", include("apps.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
