from __future__ import annotations

from celery import shared_task
from django.utils import timezone


@shared_task
def mark_timeout_games() -> int:
    """Finish active games whose running side has no remaining clock."""

    from apps.games.models import Game
    from apps.games.services import _timeout_game

    count = 0
    active_games = Game.objects.filter(status=Game.Status.ACTIVE, clock_started_at__isnull=False)
    for game in active_games.iterator():
        elapsed_ms = int((timezone.now() - game.clock_started_at).total_seconds() * 1000)
        charged_ms = max(elapsed_ms - int(game.delay_ms), 0)
        if game.turn == "white" and game.white_time_ms <= charged_ms:
            game.white_time_ms = 0
            _timeout_game(game, "white")
            count += 1
        elif game.turn == "black" and game.black_time_ms <= charged_ms:
            game.black_time_ms = 0
            _timeout_game(game, "black")
            count += 1
    return count
