from __future__ import annotations

from unittest.mock import patch

import pytest
from apps.accounts.models import User
from apps.games.services import (
    GameActor,
    ParticipantIdentity,
    apply_conditional_move,
    award_bot_level_if_won,
    create_same_pc_game,
    play_local_bot_reply,
    play_uci_move,
    serialize_game,
    set_conditional_move,
)
from apps.notifications.models import Notification
from apps.rooms.models import Room
from apps.stockfish.engine import EngineResult
from django.core.exceptions import ValidationError
from django.urls import reverse


@pytest.mark.django_db
def test_same_pc_game_accepts_legal_move():
    game = create_same_pc_game(white_name="White", black_name="Black", initial_minutes=5)
    actor = GameActor(
        identity=ParticipantIdentity(user=None, guest_key="", display_name="White"), color="white", display_name="White"
    )
    move, game = play_uci_move(game=game, actor=actor, uci="e2e4")
    assert move.san == "e4"
    assert game.turn == "black"
    assert game.ply_count == 1


@pytest.mark.django_db
def test_move_notifies_registered_opponent():
    white = User.objects.create_user(email="white@example.com", password="StrongPass123!")
    black = User.objects.create_user(email="black@example.com", password="StrongPass123!")
    game = create_same_pc_game(white_name="White", black_name="Black", initial_minutes=5)
    game.white_user = white
    game.black_user = black
    game.save(update_fields=["white_user", "black_user", "updated_at"])
    actor = GameActor(
        identity=ParticipantIdentity(user=white, guest_key="", display_name="White"),
        color="white",
        display_name="White",
    )

    play_uci_move(game=game, actor=actor, uci="e2e4")

    notice = Notification.objects.get(recipient=black, title="Your move")
    assert str(game.pk) in notice.target_url


@pytest.mark.django_db
def test_illegal_move_rejected():
    game = create_same_pc_game(white_name="White", black_name="Black", initial_minutes=5)
    actor = GameActor(
        identity=ParticipantIdentity(user=None, guest_key="", display_name="White"), color="white", display_name="White"
    )
    with pytest.raises(ValidationError):
        play_uci_move(game=game, actor=actor, uci="e2e5")


@pytest.mark.django_db
def test_correspondence_conditional_move_is_applied():
    game = create_same_pc_game(white_name="White", black_name="Black")
    room = Room.objects.create(host_display_name="White", time_category=Room.TimeCategory.DAILY,
                               clock_initial_seconds=86400)
    game.room = room
    game.save(update_fields=["room", "updated_at"])
    black = GameActor(identity=ParticipantIdentity(user=None, guest_key="black", display_name="Black"),
                      color="black", display_name="Black")
    white = GameActor(identity=ParticipantIdentity(user=None, guest_key="white", display_name="White"),
                      color="white", display_name="White")
    set_conditional_move(game=game, actor=black, expected_uci="e2e4", response_uci="e7e5")
    play_uci_move(game=game, actor=white, uci="e2e4")
    game.refresh_from_db()
    assert apply_conditional_move(game) is True
    game.refresh_from_db()
    assert game.last_move_uci == "e7e5"


@pytest.mark.django_db
def test_winning_unlocked_bot_level_advances_user_once():
    user = User.objects.create_user(email="bot-winner@example.com", password="StrongPass123!", bot_level=2)
    game = create_same_pc_game(white_name="Player", black_name="Bot")
    game.white_user = user
    game.winner_color = "white"
    game.metadata = {"mode": "local_ai", "player_color": "white", "bot_level": 2}
    game.save(update_fields=["white_user", "winner_color", "metadata", "updated_at"])

    award_bot_level_if_won(game)
    award_bot_level_if_won(game)

    user.refresh_from_db()
    game.refresh_from_db()
    assert user.bot_level == 3
    assert game.metadata["level_unlocked"] == 3
    assert game.metadata["progress_awarded"] is True


@pytest.mark.django_db
@patch("apps.stockfish.services.analyse_fen_with_stockfish")
def test_website_bot_uses_stockfish_when_available(analyse):
    analyse.return_value = EngineResult(bestmove="e7e5", depth=7)
    game = create_same_pc_game(white_name="Player", black_name="Bot")
    game.metadata = {"mode": "local_ai", "player_color": "white", "bot_level": 1}
    game.save(update_fields=["metadata", "updated_at"])
    player = GameActor(
        identity=ParticipantIdentity(user=None, guest_key="guest", display_name="Player"),
        color="white",
        display_name="Player",
    )
    play_uci_move(game=game, actor=player, uci="e2e4")
    game.refresh_from_db()
    bot = GameActor(identity=player.identity, color="black", display_name="Bot")

    play_local_bot_reply(game=game, actor=bot)

    game.refresh_from_db()
    assert game.last_move_uci == "e7e5"
    assert game.metadata["bot_engine"] == "stockfish"


@pytest.mark.django_db
def test_guest_bot_win_does_not_claim_saved_progress():
    game = create_same_pc_game(white_name="Player", black_name="Bot")
    game.winner_color = "white"
    game.metadata = {"mode": "local_ai", "player_color": "white", "bot_level": 1}
    game.save(update_fields=["winner_color", "metadata", "updated_at"])

    award_bot_level_if_won(game)

    game.refresh_from_db()
    assert game.metadata["progress_awarded"] is False
    assert "level_unlocked" not in game.metadata


@pytest.mark.django_db
def test_bot_game_page_shows_result_help_without_removed_panels(client):
    game = create_same_pc_game(white_name="Player", black_name="Bot")
    game.metadata = {"mode": "local_ai", "player_color": "white", "bot_level": 1}
    game.save(update_fields=["metadata", "updated_at"])

    response = client.get(reverse("games:play", args=[game.pk]))

    assert response.status_code == 200
    assert b"Sign in" in response.content
    assert b"Move History" not in response.content
    assert b"Current Position" not in response.content
    assert b"game-result-modal" in response.content
    assert b"New game" in response.content
    assert b"Share result" in response.content


@pytest.mark.django_db
def test_serialized_game_contains_board_and_legal_moves():
    game = create_same_pc_game(white_name="White", black_name="Black", initial_minutes=5)
    payload = serialize_game(game)
    assert payload["turn"] == "white"
    assert len(payload["board"]) == 8
    assert any(move["uci"] == "e2e4" for move in payload["legal_moves"])
