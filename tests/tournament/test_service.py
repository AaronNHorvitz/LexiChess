from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

from lexichess.config import AppSettings
from lexichess.llm.base import MoveProvider, ProviderCapabilities, ProviderHealthReport
from lexichess.llm.types import MoveRequest, ProviderResponse
from lexichess.storage import SQLiteRepository
from lexichess.tournament.models import PlayerSpec
from lexichess.tournament.service import (
    create_round_robin_tournament,
    run_tournament,
)


class FakeTournamentProvider(MoveProvider):
    def __init__(self, provider_name: str, model: str, outputs: list[str]) -> None:
        self.provider_name = provider_name
        self.model = model
        self._outputs = outputs

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_sync_requests=True,
            supports_health_checks=True,
            local_only=True,
        )

    def health_check(self) -> ProviderHealthReport:
        return ProviderHealthReport(
            provider_name=self.provider_name,
            model=self.model,
            is_healthy=True,
            model_available=True,
            capabilities=self.capabilities(),
        )

    def request_move(self, request: MoveRequest) -> ProviderResponse:
        del request
        output = self._outputs.pop(0)
        return ProviderResponse(
            provider=self.provider_name,
            model=self.model,
            output_text=output,
            raw_response={"text": output},
            latency_ms=1,
        )


def test_run_tournament_can_pause_and_resume(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    repository = SQLiteRepository(tmp_path / "service_tournaments.db")
    settings = AppSettings.from_env()
    tournament_id = create_round_robin_tournament(
        repository,
        name="Resume Test",
        players=[
            PlayerSpec("ollama", "qwen3:8b"),
            PlayerSpec("stockfish", "stockfish_beginner"),
        ],
        double_round_robin=True,
    )

    scripts = {
        ("ollama", "qwen3:8b"): [["e4"], ["banana", "still bad"]],
        ("stockfish", "stockfish_beginner"): [["banana", "still bad"], ["e4"]],
    }
    creation_counts: dict[tuple[str, str], int] = defaultdict(int)

    def fake_build_provider(
        provider_name: str,
        settings: AppSettings,
        *,
        model: str | None = None,
    ) -> FakeTournamentProvider:
        del settings
        resolved_model = model or "unknown"
        key = (provider_name, resolved_model)
        index = creation_counts[key]
        creation_counts[key] += 1
        return FakeTournamentProvider(
            provider_name, resolved_model, scripts[key][index]
        )

    monkeypatch.setattr(
        "lexichess.tournament.service.build_provider", fake_build_provider
    )

    first_summary = run_tournament(
        repository,
        tournament_id=tournament_id,
        settings=settings,
        max_matches=1,
        record_engine_analysis=False,
    )
    second_summary = run_tournament(
        repository,
        tournament_id=tournament_id,
        settings=settings,
        record_engine_analysis=False,
    )

    assert first_summary.status == "paused"
    assert first_summary.completed_pairings == 1
    assert first_summary.pending_pairings == 1
    assert second_summary.status == "completed"
    assert second_summary.completed_pairings == 2
    assert second_summary.pending_pairings == 0
    assert second_summary.standings[0]["points"] == 1.0
    assert second_summary.standings[1]["points"] == 1.0


def test_run_tournament_can_retry_failed_pairings(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    repository = SQLiteRepository(tmp_path / "service_failed_tournaments.db")
    settings = AppSettings.from_env()
    tournament_id = create_round_robin_tournament(
        repository,
        name="Failure Recovery",
        players=[
            PlayerSpec("ollama", "qwen3:8b"),
            PlayerSpec("stockfish", "stockfish_beginner"),
        ],
        double_round_robin=False,
    )

    call_count = {"count": 0}

    def failing_build_provider(
        provider_name: str,
        settings: AppSettings,
        *,
        model: str | None = None,
    ) -> FakeTournamentProvider:
        del provider_name, settings, model
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise RuntimeError("temporary provider failure")
        return FakeTournamentProvider("ollama", "qwen3:8b", ["e4"])

    monkeypatch.setattr(
        "lexichess.tournament.service.build_provider",
        failing_build_provider,
    )

    failed_summary = run_tournament(
        repository,
        tournament_id=tournament_id,
        settings=settings,
        record_engine_analysis=False,
    )

    assert failed_summary.status == "paused"
    assert failed_summary.failed_pairings == 1

    def recovered_build_provider(
        provider_name: str,
        settings: AppSettings,
        *,
        model: str | None = None,
    ) -> FakeTournamentProvider:
        del settings
        resolved_model = model or "unknown"
        if provider_name == "ollama":
            return FakeTournamentProvider(provider_name, resolved_model, ["e4"])
        return FakeTournamentProvider(
            provider_name, resolved_model, ["banana", "still bad"]
        )

    monkeypatch.setattr(
        "lexichess.tournament.service.build_provider",
        recovered_build_provider,
    )

    recovered_summary = run_tournament(
        repository,
        tournament_id=tournament_id,
        settings=settings,
        include_failed=True,
        record_engine_analysis=False,
    )

    assert recovered_summary.status == "completed"
    assert recovered_summary.failed_pairings == 0
    assert recovered_summary.completed_pairings == 1
