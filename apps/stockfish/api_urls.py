from django.urls import path

from apps.stockfish.api_views import MobileBestMoveAPIView

app_name = "stockfish_api"

urlpatterns = [
    path("stockfish/best-move/", MobileBestMoveAPIView.as_view(), name="best-move"),
]
