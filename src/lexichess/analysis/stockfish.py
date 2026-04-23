from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import chess
import chess.engine

@dataclass(frozen=True, slots=True)
class EngineAnalysis:
    multipv_rank: int
    best_move_uci: str | None
    best_move_san: str | None
    score_cp: int | None
    score_mate: int | None
    pv_uci: tuple[str, ...]
    pv_san: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EngineHealthReport:
    engine_path: str
    is_healthy: bool
    engine_name: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


EngineFactory = Callable[[str], Any]


class StockfishEngine:
    def __init__(
        self,
        *,
        path: str = "stockfish",
        depth: int = 12,
        multipv: int = 3,
        movetime_ms: int | None = None,
        engine_factory: EngineFactory | None = None,
    ) -> None:
        self.path = path
        self.depth = depth
        self.multipv = multipv
        self.movetime_ms = movetime_ms
        self._engine_factory = engine_factory or chess.engine.SimpleEngine.popen_uci

    def health_check(self) -> EngineHealthReport:
        try:
            engine = self._engine_factory(self.path)
        except Exception as exc:
            return EngineHealthReport(
                engine_path=self.path,
                is_healthy=False,
                error_message=str(exc),
            )

        try:
            engine_name = engine.id.get("name") if hasattr(engine, "id") else None
            return EngineHealthReport(
                engine_path=self.path,
                is_healthy=True,
                engine_name=str(engine_name) if engine_name else None,
                metadata={
                    "depth": self.depth,
                    "multipv": self.multipv,
                    "movetime_ms": self.movetime_ms,
                },
            )
        finally:
            engine.quit()

    def analyze(
        self,
        fen: str | None = None,
        *,
        depth: int | None = None,
        multipv: int | None = None,
    ) -> list[EngineAnalysis]:
        board = chess.Board(fen) if fen else chess.Board()
        engine = self._engine_factory(self.path)
        try:
            info = engine.analyse(
                board,
                self._build_limit(depth=depth),
                multipv=multipv or self.multipv,
            )
        finally:
            engine.quit()

        rows = info if isinstance(info, list) else [info]
        return [
            _normalize_analysis_row(board, row, rank=index + 1)
            for index, row in enumerate(rows)
        ]

    def _build_limit(self, *, depth: int | None = None) -> chess.engine.Limit:
        if self.movetime_ms is not None:
            return chess.engine.Limit(time=self.movetime_ms / 1000.0)
        return chess.engine.Limit(depth=depth or self.depth)


def _normalize_analysis_row(
    board: chess.Board,
    row: Mapping[str, Any],
    *,
    rank: int,
) -> EngineAnalysis:
    pv_moves = row.get("pv") or []
    pv_uci = tuple(move.uci() for move in pv_moves)
    pv_san = _pv_to_san(board, pv_moves)
    best_move_uci = pv_uci[0] if pv_uci else None
    best_move_san = pv_san[0] if pv_san else None

    score = row.get("score")
    score_cp: int | None = None
    score_mate: int | None = None
    if isinstance(score, chess.engine.PovScore):
        white_score = score.white()
        score_cp = white_score.score()
        score_mate = white_score.mate()

    return EngineAnalysis(
        multipv_rank=rank,
        best_move_uci=best_move_uci,
        best_move_san=best_move_san,
        score_cp=score_cp,
        score_mate=score_mate,
        pv_uci=pv_uci,
        pv_san=pv_san,
    )


def _pv_to_san(board: chess.Board, pv_moves: list[chess.Move]) -> tuple[str, ...]:
    replay = board.copy()
    san_moves: list[str] = []
    for move in pv_moves:
        san_moves.append(replay.san(move))
        replay.push(move)
    return tuple(san_moves)
