from __future__ import annotations

import json
from pathlib import Path

import chess
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from lexichess.cli import main
from lexichess.llm.base import MoveProvider, ProviderCapabilities, ProviderHealthReport
from lexichess.llm.types import MoveRequest, ProviderResponse
from lexichess.storage import SQLiteRepository


def test_settings_command_prints_resolved_settings(
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEXICHESS_ENV_PROFILE", "staging")
    monkeypatch.setenv("LEXICHESS_LOG_FORMAT_JSON", "true")

    exit_code = main(["settings", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["environment_profile"] == "staging"
    assert payload["logging"]["json"] is True


def test_settings_command_redacts_secret_api_key(
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "super-secret")

    exit_code = main(["settings", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["ollama"]["api_key"] == "***REDACTED***"


def test_cli_can_list_inspect_replay_and_export_games(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    repository = SQLiteRepository(tmp_path / "cli.db")
    repository.initialize()
    game_id = repository.create_game(
        white_provider="ollama",
        white_model="qwen3:8b",
        black_provider="ollama",
        black_model="deepseek-r1:14b",
        initial_fen=chess.STARTING_FEN,
    )
    repository.log_turn(
        game_id=game_id,
        ply=1,
        attempt=1,
        color="white",
        provider="ollama",
        model="qwen3:8b",
        prompt_kind="benchmark_move",
        prompt_version="benchmark_move.v2",
        prompt="prompt",
        instructions="instructions",
        raw_response_text="MOVE: e4",
        raw_response_json={"text": "MOVE: e4"},
        candidate_move="e4",
        parsed_move_san="e4",
        parsed_move_uci="e2e4",
        fen_before=chess.STARTING_FEN,
        fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        is_legal=True,
        latency_ms=5,
        error=None,
    )
    repository.log_engine_analysis(
        game_id=game_id,
        turn_id=1,
        ply=1,
        analyzed_fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        engine_path="stockfish",
        engine_depth=12,
        engine_multipv=1,
        engine_movetime_ms=None,
        lines=[],
    )
    repository.finish_game(
        game_id,
        status="completed",
        result="*",
        termination_reason="manual_test",
    )

    assert (
        main(["list-games", "--db-path", str(repository.database_path), "--json"]) == 0
    )
    listed = json.loads(capsys.readouterr().out)
    assert listed[0]["id"] == game_id

    assert (
        main(
            [
                "inspect-game",
                str(game_id),
                "--db-path",
                str(repository.database_path),
                "--json",
            ]
        )
        == 0
    )
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["game"]["id"] == game_id
    assert inspected["moves"] == ["e4"]
    assert "engine_analyses" in inspected

    assert (
        main(["replay", str(game_id), "--db-path", str(repository.database_path)]) == 0
    )
    replay_output = capsys.readouterr().out
    assert "1. e4" in replay_output

    export_path = tmp_path / "game.pgn"
    assert (
        main(
            [
                "export-game",
                str(game_id),
                "--db-path",
                str(repository.database_path),
                "--format",
                "pgn",
                "--output",
                str(export_path),
            ]
        )
        == 0
    )
    assert "1. e4" in export_path.read_text()


def test_cli_lists_engine_anchors_and_previews_elo(
    capsys: CaptureFixture[str],
) -> None:
    assert main(["list-anchors", "--json"]) == 0
    anchors = json.loads(capsys.readouterr().out)
    assert len(anchors) >= 5
    assert anchors[0]["identity"]["runtime"] == "stockfish"

    assert (
        main(
            [
                "elo-preview",
                "--player-rating",
                "1500",
                "--opponent-rating",
                "1600",
                "--result",
                "win",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["new_rating"] > 1500


def test_cli_can_rate_game_and_list_rating_history(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    repository = SQLiteRepository(tmp_path / "ratings_cli.db")
    repository.initialize()
    game_id = repository.create_game(
        white_provider="stockfish",
        white_model="stockfish_club",
        black_provider="ollama",
        black_model="qwen3:8b",
        initial_fen=chess.STARTING_FEN,
        status="completed",
    )
    repository.log_turn(
        game_id=game_id,
        ply=1,
        attempt=1,
        color="white",
        provider="stockfish",
        model="stockfish_club",
        prompt_kind="engine_move",
        prompt_version="engine_anchor",
        prompt="engine",
        instructions="engine",
        raw_response_text="e4",
        raw_response_json={"best_move_san": "e4"},
        candidate_move="e4",
        parsed_move_san="e4",
        parsed_move_uci="e2e4",
        fen_before=chess.STARTING_FEN,
        fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        is_legal=True,
        latency_ms=1,
        error=None,
    )
    repository.finish_game(
        game_id,
        status="completed",
        result="1-0",
        termination_reason="checkmate",
    )

    assert (
        main(["rate-game", str(game_id), "--db-path", str(repository.database_path)])
        == 0
    )
    rated = json.loads(capsys.readouterr().out)
    assert rated["white"]["slug"].startswith("stockfish:stockfish_club")
    assert rated["black"]["after"] != rated["black"]["before"]

    assert (
        main(["list-ratings", "--db-path", str(repository.database_path), "--json"])
        == 0
    )
    listed = json.loads(capsys.readouterr().out)
    assert len(listed) == 2

    slug = rated["white"]["slug"]
    assert (
        main(
            [
                "rating-history",
                slug,
                "--db-path",
                str(repository.database_path),
                "--json",
            ]
        )
        == 0
    )
    history = json.loads(capsys.readouterr().out)
    assert len(history) == 1


class FakeBatchProvider(MoveProvider):
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


def test_cli_can_run_anchor_benchmark(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
) -> None:
    provider_outputs = {
        ("ollama", "qwen3:8b"): ["e4"],
        ("stockfish", "stockfish_beginner"): ["banana", "still not a move"],
    }

    def fake_build_provider(
        provider_name: str,
        settings: object,
        *,
        model: str | None = None,
    ) -> FakeBatchProvider:
        del settings
        resolved_model = model or "unknown"
        outputs = provider_outputs[(provider_name, resolved_model)]
        return FakeBatchProvider(provider_name, resolved_model, list(outputs))

    monkeypatch.setenv("LEXICHESS_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setattr(
        "lexichess.tournament.benchmark.build_provider", fake_build_provider
    )

    database_path = tmp_path / "anchor_benchmark.db"
    assert (
        main(
            [
                "run-anchor-benchmark",
                "--challenger-provider",
                "ollama",
                "--challenger-model",
                "qwen3:8b",
                "--anchor",
                "stockfish_beginner",
                "--games-per-anchor",
                "1",
                "--max-plies",
                "2",
                "--skip-analysis",
                "--db-path",
                str(database_path),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    repository = SQLiteRepository(database_path)

    assert payload["scheduled_matches"] == 1
    assert payload["matches"][0]["result"] == "1-0"
    assert len(repository.list_games()) == 1
    assert len(repository.list_latest_ratings()) == 2


def test_cli_can_create_inspect_and_run_tournament(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: MonkeyPatch,
) -> None:
    scripts = {
        ("ollama", "qwen3:8b"): [["e4"]],
        ("stockfish", "stockfish_beginner"): [["banana", "still bad"]],
    }

    def fake_build_provider(
        provider_name: str,
        settings: object,
        *,
        model: str | None = None,
    ) -> FakeBatchProvider:
        del settings
        resolved_model = model or "unknown"
        outputs = scripts[(provider_name, resolved_model)].pop(0)
        return FakeBatchProvider(provider_name, resolved_model, outputs)

    monkeypatch.setattr(
        "lexichess.tournament.service.build_provider", fake_build_provider
    )

    database_path = tmp_path / "persistent_tournaments.db"
    assert (
        main(
            [
                "create-tournament",
                "--name",
                "Opening Night",
                "--format",
                "round-robin",
                "--player",
                "ollama:qwen3:8b",
                "--player",
                "stockfish:stockfish_beginner",
                "--single-round",
                "--db-path",
                str(database_path),
                "--json",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    tournament_id = created["tournament"]["id"]
    assert len(created["pairings"]) == 1

    assert main(["list-tournaments", "--db-path", str(database_path), "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed[0]["name"] == "Opening Night"

    assert (
        main(
            [
                "run-tournament",
                str(tournament_id),
                "--db-path",
                str(database_path),
                "--skip-analysis",
                "--json",
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    repository = SQLiteRepository(database_path)

    assert summary["status"] == "completed"
    assert summary["completed_pairings"] == 1
    assert summary["standings"][0]["points"] == 1.0
    assert len(repository.list_latest_ratings()) == 2

    assert (
        main(
            [
                "inspect-tournament",
                str(tournament_id),
                "--db-path",
                str(database_path),
                "--json",
            ]
        )
        == 0
    )
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["tournament"]["status"] == "completed"
    assert inspected["pairings"][0]["result"] == "1-0"
