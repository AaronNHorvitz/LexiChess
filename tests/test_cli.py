from __future__ import annotations

import json
from pathlib import Path

import chess
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from lexichess.cli import main
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
    repository.finish_game(
        game_id,
        status="completed",
        result="*",
        termination_reason="manual_test",
    )

    assert main(["list-games", "--db-path", str(repository.database_path), "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed[0]["id"] == game_id

    assert (
        main(["inspect-game", str(game_id), "--db-path", str(repository.database_path), "--json"])
        == 0
    )
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["game"]["id"] == game_id
    assert inspected["moves"] == ["e4"]

    assert main(["replay", str(game_id), "--db-path", str(repository.database_path)]) == 0
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
