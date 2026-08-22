from __future__ import annotations

import io
from collections import Counter
from typing import Any

import chess
import chess.pgn
from django.conf import settings
from django.db import transaction
from django.db.models import Q

from apps.analysis.models import GameAnalysisJob, MoveReview, OpeningBookLine, OpeningExplorerQuery, PositionAnalysis
from apps.games.models import Game, GameMove
from apps.games.services import board_from_fen
from apps.stockfish.engine import EngineResult
from apps.stockfish.models import StockfishEngineProfile
from apps.stockfish.services import analyse_fen_with_stockfish

MATE_SCORE_CP = 100000


def engine_score_to_white_cp(*, board: chess.Board, result: EngineResult) -> int | None:
    """Convert UCI side-to-move score into a white-positive centipawn value."""

    if result.mate_score is not None:
        relative = MATE_SCORE_CP if result.mate_score > 0 else -MATE_SCORE_CP
    elif result.score_cp is not None:
        relative = int(result.score_cp)
    else:
        return None
    return relative if board.turn == chess.WHITE else -relative


def san_for_uci(fen: str, uci: str) -> str:
    if not uci or uci == "0000":
        return ""
    board = board_from_fen(fen)
    move = chess.Move.from_uci(uci)
    if move not in board.legal_moves:
        return uci
    return board.san(move)


def analyse_position(
    *,
    fen: str,
    profile: StockfishEngineProfile | None = None,
    game: Game | None = None,
    job: GameAnalysisJob | None = None,
    move: GameMove | None = None,
    depth: int | None = None,
    movetime_ms: int | None = None,
    multipv: int = 1,
) -> PositionAnalysis:
    board = board_from_fen(fen)
    result = analyse_fen_with_stockfish(
        fen=fen,
        profile=profile,
        game=game,
        depth=depth,
        movetime_ms=movetime_ms,
        multipv=multipv,
        command_type="game_review" if job else "analysis_board",
    )
    best_san = san_for_uci(fen, result.bestmove)
    white_cp = engine_score_to_white_cp(board=board, result=result)
    return PositionAnalysis.objects.create(
        job=job,
        game=game,
        move=move,
        fen=fen,
        side_to_move="white" if board.turn == chess.WHITE else "black",
        depth=result.depth or int(depth or 0),
        movetime_ms=int(movetime_ms or 0),
        multipv=multipv,
        bestmove_uci=result.bestmove,
        bestmove_san=best_san,
        score_cp=result.score_cp,
        score_white_cp=white_cp,
        mate_score=result.mate_score,
        pv=result.pv,
        raw_engine=result.raw_info,
    )


def classify_move(
    *, played_uci: str, best_uci: str, mover_color: str, before_white_cp: int | None, after_white_cp: int | None
) -> tuple[str, int, str]:
    if before_white_cp is None or after_white_cp is None:
        return MoveReview.Classification.UNKNOWN, 0, "Engine score unavailable for this move."
    if best_uci and played_uci == best_uci:
        return MoveReview.Classification.BEST, 0, "Best engine move."
    before_for_mover = before_white_cp if mover_color == "white" else -before_white_cp
    after_for_mover = after_white_cp if mover_color == "white" else -after_white_cp
    loss = max(int(before_for_mover - after_for_mover), 0)
    if loss <= 25:
        return MoveReview.Classification.EXCELLENT, loss, "Very close to the best continuation."
    if loss <= 60:
        return MoveReview.Classification.GOOD, loss, "Good practical move."
    if loss <= 120:
        return MoveReview.Classification.INACCURACY, loss, "Small evaluation loss."
    if loss <= 300:
        return MoveReview.Classification.MISTAKE, loss, "Significant evaluation loss."
    return MoveReview.Classification.BLUNDER, loss, "Major evaluation loss."


@transaction.atomic
def create_analysis_job(
    *,
    game: Game,
    requested_by: Any | None = None,
    analysis_type: str = GameAnalysisJob.AnalysisType.QUICK,
    depth: int | None = None,
) -> GameAnalysisJob:
    profile = StockfishEngineProfile.default_profile()
    selected_depth = int(depth or getattr(settings, "ANALYSIS_REVIEW_DEPTH", profile.default_depth))
    selected_depth = min(selected_depth, int(getattr(settings, "ANALYSIS_MAX_DEPTH", 18)))
    return GameAnalysisJob.objects.create(
        game=game,
        requested_by=requested_by if getattr(requested_by, "is_authenticated", False) else None,
        engine_profile=profile,
        analysis_type=analysis_type,
        depth=selected_depth,
        movetime_ms=profile.default_movetime_ms,
    )


def run_game_review(*, job: GameAnalysisJob) -> dict[str, Any]:
    job.mark_running()
    game = Game.objects.prefetch_related("moves").get(pk=job.game_id)
    moves = list(game.moves.all().order_by("ply_number"))
    total = max(len(moves), 1)
    summary_counter: Counter[str] = Counter()
    evaluation_points: list[dict[str, Any]] = []
    try:
        for index, move in enumerate(moves, start=1):
            before_position = analyse_position(
                fen=move.fen_before,
                profile=job.engine_profile,
                game=game,
                job=job,
                move=move,
                depth=job.depth,
                movetime_ms=job.movetime_ms,
            )
            after_position = analyse_position(
                fen=move.fen_after,
                profile=job.engine_profile,
                game=game,
                job=job,
                move=move,
                depth=job.depth,
                movetime_ms=job.movetime_ms,
            )
            classification, loss, comment = classify_move(
                played_uci=move.uci,
                best_uci=before_position.bestmove_uci,
                mover_color=move.color,
                before_white_cp=before_position.score_white_cp,
                after_white_cp=after_position.score_white_cp,
            )
            MoveReview.objects.update_or_create(
                job=job,
                ply_number=move.ply_number,
                defaults={
                    "game": game,
                    "move": move,
                    "move_uci": move.uci,
                    "move_san": move.san,
                    "classification": classification,
                    "before_score_white_cp": before_position.score_white_cp,
                    "after_score_white_cp": after_position.score_white_cp,
                    "bestmove_uci": before_position.bestmove_uci,
                    "bestmove_san": before_position.bestmove_san,
                    "score_loss_cp": loss,
                    "comment": comment,
                    "best_line": before_position.pv,
                    "fen_before": move.fen_before,
                    "fen_after": move.fen_after,
                },
            )
            summary_counter[classification] += 1
            evaluation_points.append(
                {
                    "ply": move.ply_number,
                    "move": move.san,
                    "score_white_cp": after_position.score_white_cp,
                    "classification": classification,
                }
            )
            job.progress = min(99, int((index / total) * 100))
            job.save(update_fields=["progress", "updated_at"])
        losses = {"white": [], "black": []}
        for review in job.move_reviews.all():
            losses[moves[review.ply_number - 1].color].append(review.score_loss_cp)
        accuracy = {color: round(100 * (2.718281828 ** (-(sum(values) / max(len(values), 1)) / 300)), 1) if values else 100.0 for color, values in losses.items()}
        summary = {"counts": dict(summary_counter), "moves": len(moves), "evaluation": evaluation_points, "accuracy": accuracy}
        job.mark_completed(summary=summary)
        from apps.games.tasks import evaluate_fair_play
        transaction.on_commit(lambda: evaluate_fair_play.delay(str(game.pk)))
        return summary
    except Exception as exc:
        job.mark_failed(str(exc))
        raise


def serialize_job(job: GameAnalysisJob) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "game": str(job.game_id),
        "status": job.status,
        "analysis_type": job.analysis_type,
        "depth": job.depth,
        "movetime_ms": job.movetime_ms,
        "progress": job.progress,
        "summary": job.summary,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


def serialize_move_review(review: MoveReview) -> dict[str, Any]:
    return {
        "ply_number": review.ply_number,
        "move_uci": review.move_uci,
        "move_san": review.move_san,
        "classification": review.classification,
        "before_score_white_cp": review.before_score_white_cp,
        "after_score_white_cp": review.after_score_white_cp,
        "bestmove_uci": review.bestmove_uci,
        "bestmove_san": review.bestmove_san,
        "score_loss_cp": review.score_loss_cp,
        "comment": review.comment,
        "best_line": review.best_line,
    }


def personal_opening_statistics(user: Any) -> list[dict[str, Any]]:
    games = Game.objects.filter(Q(white_user=user) | Q(black_user=user), status=Game.Status.FINISHED).prefetch_related("moves")
    stats: dict[str, dict[str, Any]] = {}
    openings = list(OpeningBookLine.objects.filter(is_active=True).order_by("-frequency"))
    for game in games:
        played = [move.uci for move in game.moves.all().order_by("ply_number")]
        match = next((line for line in openings if played[:len(line.moves_uci)] == line.moves_uci), None)
        if not match:
            continue
        row = stats.setdefault(match.eco, {"eco": match.eco, "name": match.name, "games": 0, "wins": 0, "draws": 0, "losses": 0})
        row["games"] += 1
        is_white = game.white_user_id == user.pk
        if game.result == Game.Result.DRAW:
            row["draws"] += 1
        elif (game.result == Game.Result.WHITE_WIN) == is_white:
            row["wins"] += 1
        else:
            row["losses"] += 1
    return sorted(stats.values(), key=lambda row: -row["games"])


def parse_pgn_moves_to_uci(pgn_text: str) -> list[str]:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return []
    board = game.board()
    moves: list[str] = []
    for move in game.mainline_moves():
        moves.append(move.uci())
        board.push(move)
    return moves


def search_openings(
    *, moves_uci: list[str], user: Any | None = None, request: Any | None = None
) -> list[OpeningBookLine]:
    queryset = OpeningBookLine.objects.filter(is_active=True)
    if moves_uci:
        queryset = queryset.filter(moves_uci__contains=moves_uci)
    results = list(queryset.order_by("-frequency", "eco")[:20])
    ip_address = None
    if request is not None:
        ip_address = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0] or None
    OpeningExplorerQuery.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        moves_uci=moves_uci,
        result_count=len(results),
        ip_address=ip_address,
    )
    return results


def opening_to_dict(opening: OpeningBookLine) -> dict[str, Any]:
    return {
        "eco": opening.eco,
        "name": opening.name,
        "moves_uci": opening.moves_uci,
        "moves_san": opening.moves_san,
        "fen_after": opening.fen_after,
        "frequency": opening.frequency,
        "white_win_rate": float(opening.white_win_rate),
        "draw_rate": float(opening.draw_rate),
        "black_win_rate": float(opening.black_win_rate),
    }
