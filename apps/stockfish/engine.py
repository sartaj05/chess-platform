from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Iterable


class StockfishUnavailableError(RuntimeError):
    """Raised when the configured Stockfish executable cannot be used."""


@dataclass(frozen=True)
class EngineResult:
    """Result returned by a Stockfish UCI search."""

    bestmove: str
    ponder: str = ""
    score_cp: int | None = None
    mate_score: int | None = None
    depth: int = 0
    seldepth: int = 0
    nodes: int = 0
    nps: int = 0
    multipv: int = 1
    pv: list[str] = field(default_factory=list)
    raw_info: dict[str, object] = field(default_factory=dict)
    duration_ms: int = 0

    @property
    def has_mate_score(self) -> bool:
        return self.mate_score is not None


class StockfishClient:
    """Small robust UCI client for the local offline Stockfish binary."""

    SCORE_RE = re.compile(r"score\s+(cp|mate)\s+(-?\d+)")

    def __init__(
        self,
        *,
        binary_path: str,
        threads: int = 1,
        hash_mb: int = 64,
        skill_level: int = 20,
        startup_timeout: float = 8.0,
    ) -> None:
        resolved = self.resolve_binary(binary_path)
        if resolved is None:
            raise StockfishUnavailableError(f"Stockfish binary not found: {binary_path}")
        self.binary_path = resolved
        self.threads = max(int(threads), 1)
        self.hash_mb = max(int(hash_mb), 1)
        self.skill_level = min(max(int(skill_level), 0), 20)
        self.startup_timeout = startup_timeout
        self.process: subprocess.Popen[str] | None = None

    @staticmethod
    def resolve_binary(binary_path: str) -> str | None:
        candidates: list[str] = []
        if binary_path:
            candidates.append(binary_path)
        candidates.extend(["/usr/games/stockfish", "/usr/bin/stockfish", "stockfish"])
        for candidate in candidates:
            if os.path.isabs(candidate) and os.path.exists(candidate) and os.access(candidate, os.X_OK):
                return candidate
            found = shutil.which(candidate)
            if found:
                return found
        return None

    def __enter__(self) -> "StockfishClient":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.quit()

    def start(self) -> None:
        if self.process is not None:
            return
        self.process = subprocess.Popen(
            [self.binary_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._write("uci")
        self._read_until("uciok", timeout=self.startup_timeout)
        self._write(f"setoption name Threads value {self.threads}")
        self._write(f"setoption name Hash value {self.hash_mb}")
        self._write(f"setoption name Skill Level value {self.skill_level}")
        self._write("isready")
        self._read_until("readyok", timeout=self.startup_timeout)

    def quit(self) -> None:
        if self.process is None:
            return
        try:
            self._write("quit")
            self.process.wait(timeout=2)
        except Exception:
            self.process.kill()
        finally:
            self.process = None

    def analyse_fen(self, *, fen: str, depth: int = 12, movetime_ms: int = 0, multipv: int = 1) -> EngineResult:
        self.start()
        start = time.monotonic()
        self._write(f"setoption name MultiPV value {max(int(multipv), 1)}")
        self._write(f"position fen {fen}")
        go_parts = ["go"]
        if depth > 0:
            go_parts.extend(["depth", str(int(depth))])
        if movetime_ms > 0:
            go_parts.extend(["movetime", str(int(movetime_ms))])
        if depth <= 0 and movetime_ms <= 0:
            go_parts.extend(["movetime", "750"])
        self._write(" ".join(go_parts))
        lines = self._read_until_prefix("bestmove", timeout=max(30.0, movetime_ms / 1000 + 15.0))
        duration_ms = int((time.monotonic() - start) * 1000)
        return self._parse_result(lines, duration_ms=duration_ms)

    def _parse_result(self, lines: Iterable[str], *, duration_ms: int) -> EngineResult:
        info_lines = [line for line in lines if line.startswith("info ")]
        bestmove_line = next((line for line in reversed(list(lines)) if line.startswith("bestmove")), "bestmove 0000")
        best_parts = bestmove_line.split()
        bestmove = best_parts[1] if len(best_parts) > 1 else "0000"
        ponder = best_parts[3] if len(best_parts) > 3 and best_parts[2] == "ponder" else ""
        selected = info_lines[-1] if info_lines else ""
        score_cp: int | None = None
        mate_score: int | None = None
        score_match = self.SCORE_RE.search(selected)
        if score_match:
            value = int(score_match.group(2))
            if score_match.group(1) == "cp":
                score_cp = value
            else:
                mate_score = value
        parsed = self._parse_numeric_info(selected)
        pv: list[str] = []
        if " pv " in selected:
            pv = selected.split(" pv ", 1)[1].split()
        return EngineResult(
            bestmove=bestmove,
            ponder=ponder,
            score_cp=score_cp,
            mate_score=mate_score,
            depth=int(parsed.get("depth", 0)),
            seldepth=int(parsed.get("seldepth", 0)),
            nodes=int(parsed.get("nodes", 0)),
            nps=int(parsed.get("nps", 0)),
            multipv=int(parsed.get("multipv", 1)),
            pv=pv,
            raw_info={"lines": info_lines[-20:], "selected": selected, "bestmove_line": bestmove_line},
            duration_ms=duration_ms,
        )

    @staticmethod
    def _parse_numeric_info(line: str) -> dict[str, int]:
        parts = line.split()
        result: dict[str, int] = {}
        for idx, token in enumerate(parts[:-1]):
            if token in {"depth", "seldepth", "nodes", "nps", "multipv"}:
                try:
                    result[token] = int(parts[idx + 1])
                except ValueError:
                    continue
        return result

    def _write(self, command: str) -> None:
        if self.process is None or self.process.stdin is None:
            raise StockfishUnavailableError("Stockfish process is not running.")
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def _read_until(self, expected: str, *, timeout: float) -> list[str]:
        lines = self._read_until_prefix(expected, timeout=timeout)
        if not lines or lines[-1].strip() != expected:
            raise StockfishUnavailableError(f"Stockfish did not answer with {expected}.")
        return lines

    def _read_until_prefix(self, prefix: str, *, timeout: float) -> list[str]:
        if self.process is None or self.process.stdout is None:
            raise StockfishUnavailableError("Stockfish process is not running.")
        deadline = time.monotonic() + timeout
        lines: list[str] = []
        while time.monotonic() < deadline:
            line = self.process.stdout.readline()
            if line == "" and self.process.poll() is not None:
                raise StockfishUnavailableError("Stockfish process exited unexpectedly.")
            if not line:
                continue
            clean = line.strip()
            lines.append(clean)
            if clean.startswith(prefix):
                return lines
        raise StockfishUnavailableError(f"Timed out waiting for Stockfish response: {prefix}")
