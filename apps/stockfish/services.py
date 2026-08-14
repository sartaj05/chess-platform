from __future__ import annotations

from dataclasses import asdict
from threading import RLock
from typing import Any

from django.conf import settings

from apps.stockfish.engine import EngineResult, StockfishClient, StockfishUnavailableError
from apps.stockfish.models import StockfishEngineProfile, StockfishRun

_ENGINE_LOCK = RLock()
_ENGINE_CLIENT: StockfishClient | None = None
_ENGINE_KEY: tuple[str, int, int, int] | None = None


def _reusable_client(*, binary_path: str, threads: int, hash_mb: int, skill_level: int) -> StockfishClient:
    """Reuse one warm Stockfish process per worker to avoid startup delay."""
    global _ENGINE_CLIENT, _ENGINE_KEY
    key = (binary_path, threads, hash_mb, skill_level)
    if _ENGINE_CLIENT is None or _ENGINE_KEY != key:
        if _ENGINE_CLIENT is not None:
            _ENGINE_CLIENT.quit()
        _ENGINE_CLIENT = StockfishClient(
            binary_path=binary_path,
            threads=threads,
            hash_mb=hash_mb,
            skill_level=skill_level,
        )
        _ENGINE_CLIENT.start()
        _ENGINE_KEY = key
    return _ENGINE_CLIENT


def engine_available(binary_path: str | None = None) -> bool:
    return (
        StockfishClient.resolve_binary(binary_path or getattr(settings, "STOCKFISH_BINARY", "/usr/games/stockfish"))
        is not None
    )


def analyse_fen_with_stockfish(
    *,
    fen: str,
    profile: StockfishEngineProfile | None = None,
    game: Any | None = None,
    depth: int | None = None,
    movetime_ms: int | None = None,
    multipv: int = 1,
    command_type: str = "position_analysis",
    skill_level: int | None = None,
) -> EngineResult:
    """Run offline Stockfish and persist an engine run audit record."""

    profile = profile or StockfishEngineProfile.default_profile()
    requested_depth = int(depth if depth is not None else profile.default_depth)
    requested_movetime = int(movetime_ms if movetime_ms is not None else profile.default_movetime_ms)
    try:
        with _ENGINE_LOCK:
            client = _reusable_client(
                binary_path=profile.binary_path,
                threads=profile.threads,
                hash_mb=profile.hash_mb,
                skill_level=profile.skill_level if skill_level is None else skill_level,
            )
            result = client.analyse_fen(
                fen=fen,
                depth=requested_depth,
                movetime_ms=requested_movetime,
                multipv=multipv,
            )
        StockfishRun.objects.create(
            profile=profile,
            game=game,
            fen=fen,
            command_type=command_type,
            depth=result.depth or requested_depth,
            movetime_ms=requested_movetime,
            bestmove=result.bestmove,
            ponder=result.ponder,
            score_cp=result.score_cp,
            mate_score=result.mate_score,
            nodes=result.nodes,
            nps=result.nps,
            raw_info=result.raw_info,
            duration_ms=result.duration_ms,
            status=StockfishRun.Status.SUCCESS,
        )
        return result
    except StockfishUnavailableError as exc:
        StockfishRun.objects.create(
            profile=profile,
            game=game,
            fen=fen,
            command_type=command_type,
            depth=requested_depth,
            movetime_ms=requested_movetime,
            status=StockfishRun.Status.UNAVAILABLE,
            error_message=str(exc),
        )
        raise
    except Exception as exc:
        global _ENGINE_CLIENT, _ENGINE_KEY
        if _ENGINE_CLIENT is not None:
            _ENGINE_CLIENT.quit()
        _ENGINE_CLIENT = None
        _ENGINE_KEY = None
        StockfishRun.objects.create(
            profile=profile,
            game=game,
            fen=fen,
            command_type=command_type,
            depth=requested_depth,
            movetime_ms=requested_movetime,
            status=StockfishRun.Status.FAILED,
            error_message=str(exc),
        )
        raise


def result_to_dict(result: EngineResult) -> dict[str, Any]:
    return asdict(result)
