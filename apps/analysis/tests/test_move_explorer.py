from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.analysis.models import PositionAnalysis


@pytest.mark.django_db
@patch("apps.analysis.api_views.analyse_position")
def test_move_explorer_compares_candidate_and_returns_alternatives(analyse, client):
    analyse.side_effect = [
        PositionAnalysis(bestmove_uci="e2e4", bestmove_san="e4", score_white_cp=30, pv=["e2e4", "e7e5"]),
        PositionAnalysis(bestmove_uci="e7e5", bestmove_san="e5", score_white_cp=20, pv=["e7e5"]),
    ]
    response = client.post(
        reverse("api:analysis-explore"),
        {
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "candidate_uci": "e2e4",
            "depth": 8,
            "movetime_ms": 200,
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["candidate"]["verdict"] == "best"
    assert response.json()["alternatives"]
