import pytest

from apps.accounts.models import User
from apps.games.services import apply_elo_ratings, create_same_pc_game


@pytest.mark.django_db
def test_rated_result_updates_elo_once():
    white = User.objects.create_user(email="elo-white@example.com", password="StrongPass123!")
    black = User.objects.create_user(email="elo-black@example.com", password="StrongPass123!")
    game = create_same_pc_game(white_name="White", black_name="Black")
    game.white_user, game.black_user, game.rated = white, black, True
    game.status, game.result, game.winner_color = game.Status.FINISHED, game.Result.WHITE_WIN, "white"
    game.save()

    apply_elo_ratings(game)
    apply_elo_ratings(game)
    white.refresh_from_db(); black.refresh_from_db(); game.refresh_from_db()

    assert (white.rating, black.rating) == (1216, 1184)
    assert white.rated_games == black.rated_games == 1
    assert game.white_rating_change == 16
    assert game.ratings_applied is True
