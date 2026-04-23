from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lexichess.llm.base import MoveProvider, ProviderCapabilities, ProviderHealthReport
from lexichess.llm.types import MoveRequest, ProviderResponse
from lexichess.storage import SQLiteRepository
from lexichess.tournament import GameRunner
from lexichess.tournament.models import InvalidMoveNotification


@dataclass
class ScriptedProvider(MoveProvider):
    provider_name: str
    model: str
    outputs: list[str]

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_sync_requests=True,
            supports_system_instructions=True,
            supports_model_listing=False,
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
        output = self.outputs.pop(0)
        return ProviderResponse(
            provider=self.provider_name,
            model=self.model,
            output_text=output,
            raw_response={"text": output},
            latency_ms=1,
        )


def test_runner_plays_until_move_cap(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "runner.db")
    runner = GameRunner(
        white_provider=ScriptedProvider("ollama", "qwen3:8b", ["MOVE: e4", "Nf3"]),
        black_provider=ScriptedProvider("ollama", "deepseek-r1:14b", ["e5", "Nc6"]),
        repository=repository,
        max_plies=4,
    )

    result = runner.play()

    assert result.status == "stopped"
    assert result.termination_reason == "max_plies_reached"
    assert result.moves == ("e4", "e5", "Nf3", "Nc6")
    assert repository.list_hallucinations(result.game_id) == []


def test_runner_retries_invalid_output_and_uses_referee_callback(
    tmp_path: Path,
) -> None:
    repository = SQLiteRepository(tmp_path / "runner_retry.db")
    callback_events: list[InvalidMoveNotification] = []

    def referee_callback(notification: InvalidMoveNotification) -> str:
        callback_events.append(notification)
        return "Keep it legal and answer with one SAN move."

    runner = GameRunner(
        white_provider=ScriptedProvider("ollama", "qwen3:8b", ["e4", "Nf3"]),
        black_provider=ScriptedProvider(
            "ollama", "deepseek-r1:14b", ["banana", "MOVE: e5"]
        ),
        repository=repository,
        max_plies=3,
        referee_callback=referee_callback,
    )

    result = runner.play()
    turns = repository.list_turns(result.game_id)
    hallucinations = repository.list_hallucinations(result.game_id)

    assert result.status == "stopped"
    assert result.moves == ("e4", "e5", "Nf3")
    assert len(callback_events) == 1
    assert callback_events[0].reason == "no_candidate_found"
    assert len(hallucinations) == 1
    assert turns[1]["attempt"] == 1
    assert turns[1]["is_legal"] is False
    assert turns[1]["referee_note"] == "Keep it legal and answer with one SAN move."
    assert turns[2]["attempt"] == 2
    assert turns[2]["prompt_kind"] == "invalid_move_retry"
    assert turns[2]["is_legal"] is True


def test_runner_records_invalid_model_output_as_hallucination(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "runner_invalid.db")
    runner = GameRunner(
        white_provider=ScriptedProvider("ollama", "qwen3:8b", ["e4"]),
        black_provider=ScriptedProvider(
            "ollama", "deepseek-r1:14b", ["banana", "still not a move"]
        ),
        repository=repository,
        max_plies=4,
    )

    result = runner.play()
    hallucinations = repository.list_hallucinations(result.game_id)
    turns = repository.list_turns(result.game_id)

    assert result.status == "completed"
    assert result.result == "1-0"
    assert result.termination_reason == "no_candidate_found_black"
    assert len(hallucinations) == 2
    assert hallucinations[0]["reason"] == "no_candidate_found"
    assert turns[1]["attempt"] == 1
    assert turns[2]["attempt"] == 2
