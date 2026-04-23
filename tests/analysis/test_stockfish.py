from __future__ import annotations

from typing import Any

import chess
import chess.engine

from lexichess.analysis import StockfishEngine


class FakeEngine:
    def __init__(self) -> None:
        self.id = {"name": "FakeStockfish"}

    def analyse(
        self,
        board: chess.Board,
        limit: chess.engine.Limit,
        *,
        multipv: int = 1,
    ) -> list[dict[str, Any]]:
        del limit
        move = next(iter(board.legal_moves))
        return [
            {
                "pv": [move],
                "score": chess.engine.PovScore(chess.engine.Cp(34), chess.WHITE),
            }
            for _ in range(multipv)
        ]

    def quit(self) -> None:
        return None


def test_stockfish_health_check_and_analysis() -> None:
    engine = StockfishEngine(
        path="fake-stockfish",
        engine_factory=lambda _: FakeEngine(),
    )

    health = engine.health_check()
    analysis = engine.analyze()

    assert health.is_healthy is True
    assert health.engine_name == "FakeStockfish"
    assert len(analysis) == 3
    assert analysis[0].best_move_uci is not None
    assert analysis[0].best_move_san is not None
