from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lexichess.llm.base import MoveProvider
from lexichess.llm.types import MoveRequest, ProviderResponse
from lexichess.storage import SQLiteRepository
from lexichess.tournament import GameRunner


@dataclass
class ScriptedProvider(MoveProvider):
    provider_name: str
    model: str
    outputs: list[str]

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
        white_provider=ScriptedProvider("ollama", "qwen3:8b", ["e4", "Nf3"]),
        black_provider=ScriptedProvider("ollama", "deepseek-r1:14b", ["e5", "Nc6"]),
        repository=repository,
        max_plies=4,
    )

    result = runner.play()

    assert result.status == "stopped"
    assert result.termination_reason == "max_plies_reached"
    assert result.moves == ("e4", "e5", "Nf3", "Nc6")
    assert repository.list_hallucinations(result.game_id) == []


def test_runner_records_invalid_model_output_as_hallucination(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "runner_invalid.db")
    runner = GameRunner(
        white_provider=ScriptedProvider("ollama", "qwen3:8b", ["e4"]),
        black_provider=ScriptedProvider("ollama", "deepseek-r1:14b", ["banana"]),
        repository=repository,
        max_plies=4,
    )

    result = runner.play()
    hallucinations = repository.list_hallucinations(result.game_id)

    assert result.status == "completed"
    assert result.result == "1-0"
    assert result.termination_reason == "no_candidate_found_black"
    assert len(hallucinations) == 1
    assert hallucinations[0]["reason"] == "no_candidate_found"
