from __future__ import annotations

import pytest
from django.test import RequestFactory

from apps.games.models import Game
from apps.games.services import GameActor, ParticipantIdentity, create_same_pc_game, play_uci_move, serialize_game


@pytest.mark.django_db
def test_same_pc_game_accepts_legal_move():
    game = create_same_pc_game(white_name="White", black_name="Black", initial_minutes=5)
    actor = GameActor(identity=ParticipantIdentity(user=None, guest_key="", display_name="White"), color="white", display_name="White")
    move, game = play_uci_move(game=game, actor=actor, uci="e2e4")
    assert move.san == "e4"
    assert game.turn == "black"
    assert game.ply_count == 1


@pytest.mark.django_db
def test_illegal_move_rejected():
    game = create_same_pc_game(white_name="White", black_name="Black", initial_minutes=5)
    actor = GameActor(identity=ParticipantIdentity(user=None, guest_key="", display_name="White"), color="white", display_name="White")
    with pytest.raises(Exception):
        play_uci_move(game=game, actor=actor, uci="e2e5")


@pytest.mark.django_db
def test_serialized_game_contains_board_and_legal_moves():
    game = create_same_pc_game(white_name="White", black_name="Black", initial_minutes=5)
    payload = serialize_game(game)
    assert payload["turn"] == "white"
    assert len(payload["board"]) == 8
    assert any(move["uci"] == "e2e4" for move in payload["legal_moves"])
