from __future__ import annotations

from lexichess.analysis import EngineAnalysis, EngineHealthReport
from lexichess.llm.base import ProviderError
from lexichess.llm.providers import StockfishMoveProvider
from lexichess.llm.types import MoveRequest


class FakeStockfishEngine:
    def health_check(self) -> EngineHealthReport:
        return EngineHealthReport(
            engine_path="fake-stockfish",
            is_healthy=True,
            engine_name="FakeStockfish",
            metadata={"depth": 8, "multipv": 1},
        )

    def analyze(
        self,
        fen: str | None = None,
        *,
        depth: int | None = None,
        multipv: int | None = None,
    ) -> list[EngineAnalysis]:
        del fen, depth, multipv
        return [
            EngineAnalysis(
                multipv_rank=1,
                best_move_uci="e2e4",
                best_move_san="e4",
                score_cp=34,
                score_mate=None,
                pv_uci=("e2e4", "e7e5"),
                pv_san=("e4", "e5"),
            )
        ]


def test_stockfish_provider_returns_best_move_and_health_report() -> None:
    provider = StockfishMoveProvider(
        path="fake-stockfish",
        profile_name="stockfish_club",
        default_depth=8,
        engine=FakeStockfishEngine(),  # type: ignore[arg-type]
    )

    health = provider.health_check()
    response = provider.request_move(
        MoveRequest(
            game_id=1,
            move_number=1,
            color="white",
            fen="startpos",
            prompt="Choose a move.",
            instructions="Return one move.",
            legal_moves=("e4", "d4"),
        )
    )

    assert health.is_healthy is True
    assert health.model == "stockfish_club"
    assert response.output_text == "e4"
    assert response.raw_response is not None
    assert response.raw_response["best_move_uci"] == "e2e4"


def test_stockfish_provider_raises_when_no_best_move_exists() -> None:
    class EmptyEngine(FakeStockfishEngine):
        def analyze(
            self,
            fen: str | None = None,
            *,
            depth: int | None = None,
            multipv: int | None = None,
        ) -> list[EngineAnalysis]:
            del fen, depth, multipv
            return []

    provider = StockfishMoveProvider(
        path="fake-stockfish",
        profile_name="stockfish_club",
        default_depth=8,
        engine=EmptyEngine(),  # type: ignore[arg-type]
    )

    try:
        provider.request_move(
            MoveRequest(
                game_id=1,
                move_number=1,
                color="white",
                fen="startpos",
                prompt="Choose a move.",
                instructions="Return one move.",
                legal_moves=("e4", "d4"),
            )
        )
    except ProviderError as exc:
        assert "did not return a best move" in str(exc)
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("Expected ProviderError for empty Stockfish analysis.")
