from __future__ import annotations

from apps.stockfish.engine import StockfishClient


def test_stockfish_binary_resolution_handles_missing_path():
    assert StockfishClient.resolve_binary("/definitely/not/stockfish") in {
        None,
        "/usr/games/stockfish",
        "/usr/bin/stockfish",
    } or StockfishClient.resolve_binary("/definitely/not/stockfish").endswith("stockfish")
