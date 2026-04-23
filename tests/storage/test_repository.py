from __future__ import annotations

import chess
from pathlib import Path

from lexichess.storage import SQLiteRepository


def test_repository_initializes_and_logs_game_data(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "lexichess.db")
    repository.initialize()

    game_id = repository.create_game(
        white_provider="ollama",
        white_model="qwen3:8b",
        black_provider="ollama",
        black_model="deepseek-r1:14b",
        initial_fen=chess.STARTING_FEN,
    )
    turn_id = repository.log_turn(
        game_id=game_id,
        ply=1,
        attempt=1,
        color="white",
        provider="ollama",
        model="qwen3:8b",
        prompt_kind="benchmark_move",
        prompt_version="benchmark_move.v2",
        prompt="Choose a legal move.",
        instructions="Return one SAN move.",
        raw_response_text="e4",
        raw_response_json={"response": "e4"},
        candidate_move="e4",
        parsed_move_san="e4",
        parsed_move_uci="e2e4",
        fen_before="before",
        fen_after="after",
        is_legal=True,
        latency_ms=12,
        error=None,
    )
    repository.log_hallucination(
        game_id=game_id,
        turn_id=turn_id,
        color="black",
        provider="ollama",
        model="deepseek-r1:14b",
        raw_response_text="banana",
        candidate_move=None,
        reason="no_candidate_found",
    )
    repository.finish_game(
        game_id,
        status="completed",
        result="1-0",
        termination_reason="invalid_move_black",
    )

    game = repository.get_game(game_id)
    games = repository.list_games()
    turns = repository.list_turns(game_id)
    hallucinations = repository.list_hallucinations(game_id)

    assert game is not None
    assert game["result"] == "1-0"
    assert len(games) == 1
    assert len(turns) == 1
    assert turns[0]["parsed_move_san"] == "e4"
    assert turns[0]["raw_response_json"] == {"response": "e4"}
    assert len(hallucinations) == 1
    assert hallucinations[0]["reason"] == "no_candidate_found"
