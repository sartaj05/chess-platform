from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

app_name = "api"

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("accounts/", include("apps.accounts.api_urls")),
    path("", include("apps.notifications.api_urls")),
    path("", include("apps.stockfish.api_urls")),
    path("", include("apps.analysis.api_urls")),
    path("", include(("apps.rooms.api_urls", "rooms-api"), namespace="rooms-api")),
    path("", include(("apps.games.api_urls", "games-api"), namespace="games-api")),
]
