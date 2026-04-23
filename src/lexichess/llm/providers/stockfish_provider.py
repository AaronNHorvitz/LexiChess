from __future__ import annotations

import time
from typing import Any

from lexichess.analysis import StockfishEngine
from lexichess.index.anchors import get_engine_anchor
from lexichess.llm.base import (
    MoveProvider,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCode,
    ProviderHealthReport,
)
from lexichess.llm.types import MoveRequest, ProviderResponse


class StockfishMoveProvider(MoveProvider):
    provider_name = "stockfish"

    def __init__(
        self,
        *,
        path: str,
        profile_name: str,
        default_depth: int,
        default_multipv: int = 1,
        movetime_ms: int | None = None,
        engine: StockfishEngine | None = None,
    ) -> None:
        anchor = get_engine_anchor(profile_name)
        self.model = profile_name
        self._engine = engine or StockfishEngine(
            path=path,
            depth=anchor.depth if anchor is not None else default_depth,
            multipv=anchor.multipv if anchor is not None else default_multipv,
            movetime_ms=anchor.movetime_ms if anchor is not None else movetime_ms,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_sync_requests=True,
            supports_system_instructions=False,
            supports_model_listing=True,
            supports_health_checks=True,
            local_only=True,
        )

    def health_check(self) -> ProviderHealthReport:
        report = self._engine.health_check()
        return ProviderHealthReport(
            provider_name=self.provider_name,
            model=self.model,
            is_healthy=report.is_healthy,
            model_available=True,
            error_code=(
                None if report.is_healthy else ProviderErrorCode.MODEL_UNAVAILABLE
            ),
            error_message=report.error_message,
            capabilities=self.capabilities(),
            metadata=report.metadata,
        )

    def request_move(self, request: MoveRequest) -> ProviderResponse:
        started_at = time.perf_counter()
        try:
            lines = self._engine.analyze(
                request.fen,
                depth=None,
                multipv=1,
            )
        except Exception as exc:
            raise ProviderError(
                f"Stockfish move generation failed: {exc}",
                code=ProviderErrorCode.MODEL_UNAVAILABLE,
            ) from exc

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        if not lines or lines[0].best_move_san is None:
            raise ProviderError(
                "Stockfish did not return a best move.",
                code=ProviderErrorCode.INVALID_RESPONSE,
            )

        best_line = lines[0]
        best_move_san = best_line.best_move_san
        if best_move_san is None:
            raise ProviderError(
                "Stockfish did not return a best move.",
                code=ProviderErrorCode.INVALID_RESPONSE,
            )
        raw_response: dict[str, Any] = {
            "best_move_san": best_move_san,
            "best_move_uci": best_line.best_move_uci,
            "score_cp": best_line.score_cp,
            "score_mate": best_line.score_mate,
            "pv_san": list(best_line.pv_san),
            "pv_uci": list(best_line.pv_uci),
        }
        return ProviderResponse(
            provider=self.provider_name,
            model=self.model,
            output_text=best_move_san,
            raw_response=raw_response,
            latency_ms=latency_ms,
            finish_reason="engine_move",
        )
