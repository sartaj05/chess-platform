from __future__ import annotations

from apps.analysis.models import MoveReview
from apps.analysis.services import classify_move


def test_classify_best_move():
    classification, loss, _comment = classify_move(
        played_uci="e2e4",
        best_uci="e2e4",
        mover_color="white",
        before_white_cp=20,
        after_white_cp=25,
    )
    assert classification == MoveReview.Classification.BEST
    assert loss == 0


def test_classify_blunder_for_white():
    classification, loss, _comment = classify_move(
        played_uci="f2f3",
        best_uci="e2e4",
        mover_color="white",
        before_white_cp=30,
        after_white_cp=-500,
    )
    assert classification == MoveReview.Classification.BLUNDER
    assert loss == 530
