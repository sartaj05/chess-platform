from django.urls import path

from apps.stockfish.views import StockfishStatusView

app_name = "stockfish"

urlpatterns = [
    path("stockfish/status/", StockfishStatusView.as_view(), name="status"),
]
