from __future__ import annotations

import chess
from pathlib import Path

from lexichess.analysis import EngineAnalysis
from lexichess.index.models import CompetitorIdentity, RatingSnapshot
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


def test_repository_persists_rating_history(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "ratings.db")
    repository.initialize()

    competitor = CompetitorIdentity(
        provider="stockfish",
        model="stockfish_club",
        runtime="stockfish",
        prompt_profile="engine_anchor",
    )
    snapshot_one = RatingSnapshot(competitor=competitor, rating=1400.0, games_played=0)
    snapshot_two = RatingSnapshot(competitor=competitor, rating=1412.5, games_played=1)

    repository.record_rating_snapshot(snapshot_one, source_result="1-0")
    repository.record_rating_snapshot(snapshot_two, source_result="1-0")

    latest = repository.latest_rating_snapshot(competitor.slug)
    history = repository.list_rating_history(competitor.slug)
    listed = repository.list_latest_ratings()

    assert latest is not None
    assert latest["rating"] == 1412.5
    assert len(history) == 2
    assert listed[0]["competitor_slug"] == competitor.slug


def test_repository_persists_engine_analysis_rows(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "analysis.db")
    repository.initialize()

    game_id = repository.create_game(
        white_provider="ollama",
        white_model="qwen3:8b",
        black_provider="stockfish",
        black_model="stockfish_club",
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
        prompt="prompt",
        instructions="instructions",
        raw_response_text="e4",
        raw_response_json={"response": "e4"},
        candidate_move="e4",
        parsed_move_san="e4",
        parsed_move_uci="e2e4",
        fen_before=chess.STARTING_FEN,
        fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        is_legal=True,
        latency_ms=8,
        error=None,
    )
    repository.log_engine_analysis(
        game_id=game_id,
        turn_id=turn_id,
        ply=1,
        analyzed_fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        engine_path="stockfish",
        engine_depth=12,
        engine_multipv=2,
        engine_movetime_ms=None,
        lines=[
            EngineAnalysis(
                multipv_rank=1,
                best_move_uci="e7e5",
                best_move_san="e5",
                score_cp=20,
                score_mate=None,
                pv_uci=("e7e5", "g1f3"),
                pv_san=("e5", "Nf3"),
            ),
            EngineAnalysis(
                multipv_rank=2,
                best_move_uci="c7c5",
                best_move_san="c5",
                score_cp=15,
                score_mate=None,
                pv_uci=("c7c5", "g1f3"),
                pv_san=("c5", "Nf3"),
            ),
        ],
    )

    rows = repository.list_engine_analyses(game_id)

    assert len(rows) == 2
    assert rows[0]["turn_id"] == turn_id
    assert rows[0]["best_move_san"] == "e5"
    assert rows[0]["pv_san"] == ["e5", "Nf3"]
    assert rows[1]["multipv_rank"] == 2


def test_repository_persists_tournament_entities_and_standings(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "tournaments.db")
    repository.initialize()

    tournament_id = repository.create_tournament(
        name="Test Event",
        tournament_format="round_robin",
        config={"double_round_robin": False},
    )
    white_player_id = repository.add_tournament_player(
        tournament_id,
        provider="ollama",
        model="qwen3:8b",
        seed=1,
    )
    black_player_id = repository.add_tournament_player(
        tournament_id,
        provider="stockfish",
        model="stockfish_beginner",
        seed=2,
    )
    repository.create_tournament_pairings(
        tournament_id,
        [
            {
                "match_number": 1,
                "round_number": 1,
                "white_player_id": white_player_id,
                "black_player_id": black_player_id,
                "tag": "round_robin",
            }
        ],
    )
    pairing = repository.list_tournament_pairings(tournament_id)[0]
    repository.start_tournament_pairing(int(pairing["id"]))
    repository.finish_tournament_pairing(
        int(pairing["id"]),
        status="completed",
        game_id=None,
        result="1-0",
        termination_reason="test_win",
    )
    repository.update_tournament_status(tournament_id, status="completed")

    tournament = repository.get_tournament(tournament_id)
    players = repository.list_tournament_players(tournament_id)
    pairings = repository.list_tournament_pairings(tournament_id)
    standings = repository.compute_tournament_standings(tournament_id)

    assert tournament is not None
    assert tournament["config_json"] == {"double_round_robin": False}
    assert tournament["status"] == "completed"
    assert len(players) == 2
    assert pairings[0]["status"] == "completed"
    assert pairings[0]["white_label"] == "ollama:qwen3:8b"
    assert standings[0]["label"] == "ollama:qwen3:8b"
    assert standings[0]["points"] == 1.0
    assert standings[1]["losses"] == 1
