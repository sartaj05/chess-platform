from unittest.mock import patch

import pytest
from apps.stockfish.engine import EngineResult, StockfishUnavailableError
from django.urls import reverse


@pytest.mark.django_db
@patch("apps.stockfish.api_views.analyse_fen_with_stockfish")
def test_mobile_best_move_returns_stockfish_move(analyse, client):
    analyse.return_value = EngineResult(bestmove="e2e4", depth=8, duration_ms=120)
    response = client.post(
        reverse("api:stockfish_api:best-move"),
        {"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "level": 3},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["bestmove"] == "e2e4"
    assert analyse.call_args.kwargs["skill_level"] == 6


@pytest.mark.django_db
@patch("apps.stockfish.api_views.analyse_fen_with_stockfish", side_effect=StockfishUnavailableError("missing"))
def test_mobile_best_move_reports_unavailable(_analyse, client):
    response = client.post(
        reverse("api:stockfish_api:best-move"),
        {"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "level": 1},
        content_type="application/json",
    )
    assert response.status_code == 503
