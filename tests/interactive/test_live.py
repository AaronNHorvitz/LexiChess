from __future__ import annotations

import time
from pathlib import Path

import chess

from lexichess.config import AppSettings
from lexichess.interactive import InteractiveGameRuntime, LiveGameLoopManager
from lexichess.llm.base import MoveProvider, ProviderCapabilities, ProviderHealthReport
from lexichess.llm.types import MoveRequest, ProviderResponse
from lexichess.storage import SQLiteRepository


class SharedScriptProvider(MoveProvider):
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
        if not self._outputs:
            raise RuntimeError("No scripted output available.")
        output = self._outputs.pop(0)
        return ProviderResponse(
            provider=self.provider_name,
            model=self.model,
            output_text=output,
            raw_response={"text": output},
            latency_ms=1,
        )


class ScriptedBanterService:
    def move_banter(
        self,
        *,
        game_id: int,
        color: str,
        speaker: str,
        opponent: str | None,
        move: str,
        fen: str,
    ) -> dict[str, str]:
        del game_id, fen
        return {
            "role": "player",
            "speaker": speaker,
            "category": "banter",
            "target": opponent or "opponent",
            "message": f"{speaker} says {move} landed right on {opponent}.",
            "move": move,
            "color": color,
            "source": "model",
            "provider": "ollama",
            "model": "banter-bot",
        }

    def finish(
        self,
        *,
        game_id: int,
        winner: str | None,
        loser: str | None,
        result: str | None,
        termination_reason: str | None,
        fen: str,
    ) -> dict[str, str] | None:
        del game_id, loser, result, termination_reason, fen
        if winner is None:
            return None
        return {
            "role": "player",
            "speaker": winner,
            "category": "finish",
            "target": "crowd",
            "message": f"{winner} is already calling for the postgame mic.",
            "source": "model",
            "provider": "ollama",
            "model": "banter-bot",
        }


def test_runtime_advances_model_turn_and_waits_for_human(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "live_runtime.db")
    repository.initialize()
    settings = AppSettings.from_env(
        env={"LEXICHESS_DB_PATH": str(repository.database_path)},
        dotenv_path=None,
    )
    outputs = {("ollama", "qwen3:8b"): ["MOVE: e4"]}

    def fake_builder(
        provider_name: str, settings: AppSettings, *, model: str | None = None
    ) -> SharedScriptProvider:
        del settings
        resolved_model = model or "unknown"
        return SharedScriptProvider(
            provider_name, resolved_model, outputs[(provider_name, resolved_model)]
        )

    game_id = repository.create_game(
        white_provider="ollama",
        white_model="qwen3:8b",
        black_provider="ollama",
        black_model="qwen3:14b",
        initial_fen=chess.STARTING_FEN,
        mode="interactive",
        status="created",
    )
    repository.upsert_game_seat(
        game_id=game_id,
        color="white",
        controller="model",
        provider="ollama",
        model="qwen3:8b",
        display_name="Qwen Hero",
        claimed_by=None,
    )
    repository.upsert_game_seat(
        game_id=game_id,
        color="black",
        controller="human",
        provider="ollama",
        model="qwen3:14b",
        display_name="Bob",
        claimed_by="guest:bob",
    )

    runtime = InteractiveGameRuntime(
        repository,
        settings,
        provider_builder=fake_builder,
    )

    first = runtime.advance_once(game_id)
    second = runtime.advance_once(game_id)

    turns = repository.list_turns(game_id)
    events = repository.list_game_events(game_id)
    assert first.status == "move_applied"
    assert first.move_san == "e4"
    assert second.status == "waiting_for_human"
    assert turns[0]["parsed_move_san"] == "e4"
    assert events[0]["event_type"] == "model_move_accepted"
    assert events[1]["event_type"] == "player_banter"
    assert events[2]["event_type"] == "waiting_for_human_turn"
    assert "Qwen Hero" in events[1]["payload_json"]["message"]


def test_runtime_accepts_human_move_and_advances_model_reply(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "live_human.db")
    repository.initialize()
    settings = AppSettings.from_env(
        env={"LEXICHESS_DB_PATH": str(repository.database_path)},
        dotenv_path=None,
    )
    outputs = {("ollama", "qwen3:14b"): ["MOVE: e5"]}

    def fake_builder(
        provider_name: str, settings: AppSettings, *, model: str | None = None
    ) -> SharedScriptProvider:
        del settings
        resolved_model = model or "unknown"
        return SharedScriptProvider(
            provider_name, resolved_model, outputs[(provider_name, resolved_model)]
        )

    game_id = repository.create_game(
        white_provider="ollama",
        white_model="qwen3:8b",
        black_provider="ollama",
        black_model="qwen3:14b",
        initial_fen=chess.STARTING_FEN,
        mode="interactive",
        status="created",
    )
    repository.upsert_game_seat(
        game_id=game_id,
        color="white",
        controller="human",
        provider="ollama",
        model="qwen3:8b",
        display_name="Alice",
        claimed_by="guest:alice",
    )
    repository.upsert_game_seat(
        game_id=game_id,
        color="black",
        controller="model",
        provider="ollama",
        model="qwen3:14b",
        display_name="Qwen Villain",
        claimed_by=None,
    )

    runtime = InteractiveGameRuntime(
        repository,
        settings,
        provider_builder=fake_builder,
    )

    waiting = runtime.advance_once(game_id)
    event = runtime.submit_human_move(
        game_id,
        color="white",
        move_text="MOVE: e4",
        actor_name="Alice",
    )
    reply = runtime.advance_once(game_id)

    turns = repository.list_turns(game_id)
    assert waiting.status == "waiting_for_human"
    assert event["event_type"] == "human_move_submitted"
    assert reply.status == "move_applied"
    assert [turn["parsed_move_san"] for turn in turns if turn["is_legal"]] == [
        "e4",
        "e5",
    ]


def test_runtime_emits_referee_message_for_invalid_move(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "live_referee.db")
    repository.initialize()
    settings = AppSettings.from_env(
        env={"LEXICHESS_DB_PATH": str(repository.database_path)},
        dotenv_path=None,
    )
    outputs = {("ollama", "qwen3:8b"): ["banana", "still bad"]}

    def fake_builder(
        provider_name: str,
        settings: AppSettings,
        *,
        model: str | None = None,
    ) -> SharedScriptProvider:
        del settings
        resolved_model = model or "unknown"
        return SharedScriptProvider(
            provider_name,
            resolved_model,
            outputs[(provider_name, resolved_model)],
        )

    game_id = repository.create_game(
        white_provider="ollama",
        white_model="qwen3:8b",
        black_provider="ollama",
        black_model="qwen3:14b",
        initial_fen=chess.STARTING_FEN,
        mode="showmatch",
        status="created",
    )
    repository.upsert_game_seat(
        game_id=game_id,
        color="white",
        controller="model",
        provider="ollama",
        model="qwen3:8b",
        display_name="Qwen Hero",
        claimed_by=None,
    )
    repository.upsert_game_seat(
        game_id=game_id,
        color="black",
        controller="model",
        provider="ollama",
        model="qwen3:14b",
        display_name="Qwen Villain",
        claimed_by=None,
    )

    runtime = InteractiveGameRuntime(
        repository,
        settings,
        provider_builder=fake_builder,
    )

    result = runtime.advance_once(game_id)
    events = repository.list_game_events(game_id)

    assert result.status == "completed"
    assert result.detail == "no_candidate_found_white"
    assert any(event["event_type"] == "referee_message" for event in events)
    assert any(event["event_type"] == "game_finished" for event in events)
    referee_payloads = [
        event["payload_json"]
        for event in events
        if event["event_type"] == "referee_message"
    ]
    assert any("Reset, breathe" in payload["message"] for payload in referee_payloads)


def test_runtime_uses_injected_banter_service_for_model_moves(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "live_banter.db")
    repository.initialize()
    settings = AppSettings.from_env(
        env={"LEXICHESS_DB_PATH": str(repository.database_path)},
        dotenv_path=None,
    )
    outputs = {("ollama", "qwen3:8b"): ["MOVE: e4"]}

    def fake_builder(
        provider_name: str, settings: AppSettings, *, model: str | None = None
    ) -> SharedScriptProvider:
        del settings
        resolved_model = model or "unknown"
        return SharedScriptProvider(
            provider_name, resolved_model, outputs[(provider_name, resolved_model)]
        )

    game_id = repository.create_game(
        white_provider="ollama",
        white_model="qwen3:8b",
        black_provider="ollama",
        black_model="qwen3:14b",
        initial_fen=chess.STARTING_FEN,
        mode="showmatch",
        status="created",
    )
    repository.upsert_game_seat(
        game_id=game_id,
        color="white",
        controller="model",
        provider="ollama",
        model="qwen3:8b",
        display_name="Qwen Hero",
        claimed_by=None,
    )
    repository.upsert_game_seat(
        game_id=game_id,
        color="black",
        controller="model",
        provider="ollama",
        model="qwen3:14b",
        display_name="Qwen Villain",
        claimed_by=None,
    )

    runtime = InteractiveGameRuntime(
        repository,
        settings,
        provider_builder=fake_builder,
        banter_service=ScriptedBanterService(),
    )

    runtime.advance_once(game_id)
    events = repository.list_game_events(game_id, event_types=("player_banter",))

    assert events[0]["payload_json"]["source"] == "model"
    assert "Qwen Villain" in events[0]["payload_json"]["message"]


def test_live_loop_manager_runs_until_human_turn_and_can_stop(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "live_manager.db")
    repository.initialize()
    settings = AppSettings.from_env(
        env={"LEXICHESS_DB_PATH": str(repository.database_path)},
        dotenv_path=None,
    )
    outputs = {("ollama", "qwen3:8b"): ["MOVE: e4"]}

    def fake_builder(
        provider_name: str, settings: AppSettings, *, model: str | None = None
    ) -> SharedScriptProvider:
        del settings
        resolved_model = model or "unknown"
        return SharedScriptProvider(
            provider_name, resolved_model, outputs[(provider_name, resolved_model)]
        )

    game_id = repository.create_game(
        white_provider="ollama",
        white_model="qwen3:8b",
        black_provider="ollama",
        black_model="qwen3:14b",
        initial_fen=chess.STARTING_FEN,
        mode="interactive",
        status="created",
    )
    repository.upsert_game_seat(
        game_id=game_id,
        color="white",
        controller="model",
        provider="ollama",
        model="qwen3:8b",
        display_name="Qwen Hero",
        claimed_by=None,
    )
    repository.upsert_game_seat(
        game_id=game_id,
        color="black",
        controller="human",
        provider="ollama",
        model="qwen3:14b",
        display_name="Bob",
        claimed_by="guest:bob",
    )

    runtime = InteractiveGameRuntime(
        repository,
        settings,
        provider_builder=fake_builder,
    )
    manager = LiveGameLoopManager(runtime, repository, idle_poll_seconds=0.05)

    status = manager.start(game_id)
    assert status["running"] is True

    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        current = manager.status(game_id)
        if current["last_outcome"] == "waiting_for_human":
            break
        time.sleep(0.02)
    else:
        raise AssertionError("Live loop never reached a waiting-for-human state.")

    stopped = manager.stop(game_id)
    assert stopped["stop_requested"] is True
    assert manager.wait_for_game(game_id, timeout=1.0) is True
