from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.chat.models import Conversation, Message
from apps.friends.models import Friendship
from apps.games.models import Game
from apps.puzzles.models import Puzzle, PuzzleAttempt
from apps.tournaments.models import Tournament, TournamentEntry


@pytest.fixture
def dashboard_users(db):
    user = User.objects.create_user(email="dashboard@example.com", password="test-pass-123")
    opponent = User.objects.create_user(email="opponent@example.com", password="test-pass-123")
    return user, opponent


def test_dashboard_requires_login(client):
    assert client.get(reverse("dashboard:home")).status_code == 302


def test_dashboard_aggregates_user_activity(client, dashboard_users):
    user, opponent = dashboard_users
    Friendship.objects.create(requester=user, addressee=opponent, status=Friendship.Status.ACCEPTED)
    conversation = Conversation.objects.create(first_user=user, second_user=opponent)
    Message.objects.create(conversation=conversation, sender=opponent, body="Your move")
    Game.objects.create(
        white_user=user,
        black_user=opponent,
        white_display_name=user.display_name,
        black_display_name=opponent.display_name,
        status=Game.Status.FINISHED,
        result=Game.Result.WHITE_WIN,
    )
    puzzle = Puzzle.objects.create(
        title="Dashboard puzzle",
        initial_fen="8/8/8/8/8/8/K6k/8 w - - 0 1",
        solution_moves=["a2a3"],
    )
    PuzzleAttempt.objects.create(
        puzzle=puzzle,
        user=user,
        current_fen=puzzle.initial_fen,
        status=PuzzleAttempt.Status.SOLVED,
        solved_at=timezone.now(),
    )
    tournament = Tournament.objects.create(
        name="Dashboard Cup",
        organizer=user,
        starts_at=timezone.now() + timedelta(days=1),
    )
    TournamentEntry.objects.create(tournament=tournament, user=user)

    client.force_login(user)
    response = client.get(reverse("dashboard:home"))
    assert response.status_code == 200
    assert response.context["game_stats"] == {"total": 1, "active": 0, "wins": 1, "losses": 0, "draws": 0}
    assert response.context["friend_count"] == 1
    assert response.context["puzzle_stats"] == {"attempted": 1, "solved": 1}
    assert response.context["unread_message_count"] == 1
    assert b"Dashboard Cup" in response.content


def test_dashboard_does_not_include_other_users_activity(client, dashboard_users):
    user, opponent = dashboard_users
    third = User.objects.create_user(email="third@example.com", password="test-pass-123")
    Game.objects.create(
        white_user=opponent,
        black_user=third,
        white_display_name=opponent.display_name,
        black_display_name=third.display_name,
        status=Game.Status.FINISHED,
        result=Game.Result.WHITE_WIN,
    )
    client.force_login(user)
    response = client.get(reverse("dashboard:home"))
    assert response.context["game_stats"]["total"] == 0
    assert len(response.context["recent_games"]) == 0
