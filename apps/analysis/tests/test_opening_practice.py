import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.analysis.models import OpeningBookLine, OpeningPractice


@pytest.mark.django_db
def test_opening_spaced_repetition_grading():
    user = User.objects.create_user(email="trainer@example.com", password="StrongPass123!")
    line = OpeningBookLine.objects.create(
        eco="A00", name="Practice line", moves_uci=["e2e4"], moves_san="1. e4",
        pgn_prefix="1. e4", fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    )
    client = APIClient()
    client.force_authenticate(user)
    listing = client.get("/api/analysis/openings/practice/")
    assert listing.status_code == 200
    assert any(row["id"] == str(line.pk) and row["due"] for row in listing.data["results"])
    graded = client.post("/api/analysis/openings/practice/", {"opening_id": str(line.pk), "quality": 5})
    assert graded.status_code == 200
    assert OpeningPractice.objects.get(user=user, opening=line).repetitions == 1
