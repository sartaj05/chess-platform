from __future__ import annotations

from django.utils import timezone

from celery import shared_task


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


@shared_task
def mark_abandoned_games() -> int:
    from datetime import timedelta

    from apps.games.models import Game
    from apps.games.services import apply_elo_ratings
    count = 0
    now = timezone.now()
    for game in Game.objects.filter(status=Game.Status.ACTIVE).iterator():
        for color in ("white","black"):
            disconnected=getattr(game,f"{color}_disconnected_at")
            if disconnected and now >= disconnected + timedelta(seconds=game.reconnect_grace_seconds):
                winner = "black" if color == "white" else "white"
                game.finish(result=Game.Result.BLACK_WIN if winner == "black" else Game.Result.WHITE_WIN, termination=Game.Termination.ABANDONMENT, winner_color=winner)
                apply_elo_ratings(game)
                count += 1
                break
    return count


@shared_task
def evaluate_fair_play(game_id: str) -> dict:
    from apps.analysis.models import MoveReview
    from apps.games.models import FairPlayReview, Game
    game = Game.objects.get(pk=game_id)
    reviews = MoveReview.objects.filter(game=game).select_related("move")
    if not reviews.exists() and game.ply_count:
        from apps.analysis.services import create_analysis_job, run_game_review
        run_game_review(job=create_analysis_job(game=game, analysis_type="quick", depth=10))
        reviews=MoveReview.objects.filter(game=game).select_related("move")
    if not reviews.exists() and game.ply_count:
        from apps.analysis.services import create_analysis_job, run_game_review
        run_game_review(job=create_analysis_job(game=game, analysis_type="quick", depth=10))
        reviews = MoveReview.objects.filter(game=game).select_related("move")
    metrics = {"white": [], "black": []}
    matches = {"white": 0, "black": 0}
    for review in reviews:
        color = review.move.color
        metrics[color].append(review.score_loss_cp)
        if review.move_uci == review.bestmove_uci:
            matches[color] += 1
    rates={c:(matches[c]/len(metrics[c])*100 if metrics[c] else 0) for c in metrics}
    averages={c:round(sum(metrics[c])/len(metrics[c])) if metrics[c] else 0 for c in metrics}
    signals = []
    risk = 0
    for color in ("white","black"):
        if len(metrics[color]) >= 12 and rates[color] >= 80:
            signals.append(f"{color}_high_engine_match")
            risk += 35
        if len(metrics[color]) >= 12 and averages[color] <= 18:
            signals.append(f"{color}_very_low_loss")
            risk += 30
    review,_=FairPlayReview.objects.update_or_create(game=game,defaults={"risk_score":min(risk,100),"status":FairPlayReview.Status.FLAGGED if risk>=50 else FairPlayReview.Status.CLEAR,"white_engine_match_rate":rates['white'],"black_engine_match_rate":rates['black'],"white_avg_loss_cp":averages['white'],"black_avg_loss_cp":averages['black'],"signals":signals})
    return {"status":review.status,"risk_score":review.risk_score}
