from __future__ import annotations

from pathlib import Path

import chess
from fastapi.testclient import TestClient

from lexichess.config import AppSettings
from lexichess.index.models import CompetitorIdentity, RatingSnapshot
from lexichess.storage import SQLiteRepository
from lexichess.web import create_app


def test_web_app_exposes_api_and_spectator_pages(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "web_app.db")
    repository.initialize()

    game_id = repository.create_game(
        white_provider="ollama",
        white_model="qwen3:8b",
        black_provider="stockfish",
        black_model="stockfish_beginner",
        initial_fen=chess.STARTING_FEN,
        status="completed",
    )
    white_turn_id = repository.log_turn(
        game_id=game_id,
        ply=1,
        attempt=1,
        color="white",
        provider="ollama",
        model="qwen3:8b",
        prompt_kind="benchmark_move",
        prompt_version="benchmark_move.v2",
        prompt="prompt",
        instructions="Return one SAN move.",
        raw_response_text="e4",
        raw_response_json={"text": "e4"},
        candidate_move="e4",
        parsed_move_san="e4",
        parsed_move_uci="e2e4",
        fen_before=chess.STARTING_FEN,
        fen_after="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        is_legal=True,
        latency_ms=2,
        error=None,
    )
    black_turn_id = repository.log_turn(
        game_id=game_id,
        ply=2,
        attempt=1,
        color="black",
        provider="stockfish",
        model="stockfish_beginner",
        prompt_kind="engine_move",
        prompt_version="engine_anchor",
        prompt="engine",
        instructions="engine",
        raw_response_text="banana",
        raw_response_json={"text": "banana"},
        candidate_move=None,
        parsed_move_san=None,
        parsed_move_uci=None,
        fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        fen_after=None,
        is_legal=False,
        latency_ms=3,
        error="no_candidate_found",
        deterministic_explanation="No move found.",
    )
    repository.log_hallucination(
        game_id=game_id,
        turn_id=black_turn_id,
        color="black",
        provider="stockfish",
        model="stockfish_beginner",
        raw_response_text="banana",
        candidate_move=None,
        reason="no_candidate_found",
        details="No move found.",
    )
    repository.log_engine_analysis(
        game_id=game_id,
        turn_id=white_turn_id,
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
        result="1-0",
        termination_reason="no_candidate_found_black",
    )

    white_competitor = CompetitorIdentity(
        provider="ollama",
        model="qwen3:8b",
        runtime="ollama",
        prompt_profile="benchmark_move.v2",
    )
    black_competitor = CompetitorIdentity(
        provider="stockfish",
        model="stockfish_beginner",
        runtime="stockfish",
        prompt_profile="engine_anchor",
    )
    repository.record_rating_snapshot(
        RatingSnapshot(competitor=white_competitor, rating=1512.0, games_played=1),
        source_game_id=game_id,
        source_result="1-0",
        competitor_result="win",
    )
    repository.record_rating_snapshot(
        RatingSnapshot(competitor=black_competitor, rating=988.0, games_played=1),
        source_game_id=game_id,
        source_result="1-0",
        competitor_result="loss",
    )

    tournament_id = repository.create_tournament(
        name="Arena Night",
        tournament_format="round_robin",
        status="completed",
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
    pairing_id = repository.list_tournament_pairings(tournament_id)[0]["id"]
    repository.finish_tournament_pairing(
        int(pairing_id),
        status="completed",
        game_id=game_id,
        result="1-0",
        termination_reason="no_candidate_found_black",
    )

    settings = AppSettings.from_env(
        env={"LEXICHESS_DB_PATH": str(repository.database_path)},
        dotenv_path=None,
    )
    app = create_app(settings)
    client = TestClient(app)

    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    version = client.get("/version")
    assert version.status_code == 200
    assert "version" in version.json()

    leaderboard = client.get("/api/leaderboard?include_provisional=true")
    assert leaderboard.status_code == 200
    assert leaderboard.json()["included_competitors"] == 2

    tournaments = client.get("/api/tournaments")
    assert tournaments.status_code == 200
    assert tournaments.json()[0]["name"] == "Arena Night"

    tournament_detail = client.get(f"/api/tournaments/{tournament_id}")
    assert tournament_detail.status_code == 200
    assert tournament_detail.json()["standings"][0]["points"] == 1.0

    tournament_report = client.get(f"/api/tournaments/{tournament_id}/report.md")
    assert tournament_report.status_code == 200
    assert "# Tournament Report: Arena Night" in tournament_report.text

    games = client.get("/api/games")
    assert games.status_code == 200
    assert games.json()[0]["id"] == game_id

    game_detail = client.get(f"/api/games/{game_id}")
    assert game_detail.status_code == 200
    assert game_detail.json()["moves"] == ["e4"]
    assert len(game_detail.json()["seats"]) == 2

    replay = client.get(f"/api/games/{game_id}/replay")
    assert replay.status_code == 200
    assert replay.json()["moves"] == ["e4"]

    created_game = client.post(
        "/api/games",
        json={
            "mode": "interactive",
            "white_provider": "ollama",
            "white_model": "qwen3:8b",
            "white_display_name": "Qwen Hero",
            "black_provider": "stockfish",
            "black_model": "stockfish_beginner",
            "black_display_name": "Stockfish Villain",
        },
    )
    assert created_game.status_code == 201
    created_payload = created_game.json()
    interactive_game_id = int(created_payload["game"]["id"])
    assert created_payload["game"]["mode"] == "interactive"
    assert created_payload["seats"][0]["display_name"] == "Qwen Hero"

    seats = client.get(f"/api/games/{interactive_game_id}/seats")
    assert seats.status_code == 200
    assert seats.json()[0]["controller"] == "model"

    claimed = client.post(
        f"/api/games/{interactive_game_id}/seats/white/claim",
        json={"claimed_by": "guest:alice", "display_name": "Alice"},
    )
    assert claimed.status_code == 200
    assert claimed.json()["seat"]["controller"] == "human"

    chat = client.post(
        f"/api/games/{interactive_game_id}/chat",
        json={
            "author_name": "Alice",
            "target": "white",
            "message": "Let's play some chaos.",
        },
    )
    assert chat.status_code == 201
    assert chat.json()["event_type"] == "user_chat"

    released = client.post(
        f"/api/games/{interactive_game_id}/seats/white/release",
        json={"provider": "ollama", "model": "qwen3:14b"},
    )
    assert released.status_code == 200
    assert released.json()["seat"]["controller"] == "model"
    assert released.json()["seat"]["model"] == "qwen3:14b"

    events = client.get(f"/api/games/{interactive_game_id}/events")
    assert events.status_code == 200
    event_types = [event["event_type"] for event in events.json()]
    assert event_types == [
        "game_created",
        "seat_claimed",
        "user_chat",
        "seat_released_to_model",
    ]

    stream = client.get(f"/api/games/{interactive_game_id}/events/stream?once=true")
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
    assert "event: game_created" in stream.text
    assert "event: seat_released_to_model" in stream.text

    assert client.get("/openapi.json").status_code == 200

    home_page = client.get("/")
    assert home_page.status_code == 200
    assert "LexiChess" in home_page.text
    assert "Top Chess Index Entrants" in home_page.text

    leaderboard_page = client.get("/leaderboard")
    assert leaderboard_page.status_code == 200
    assert "Current ladder snapshot" in leaderboard_page.text

    tournament_page = client.get(f"/tournaments/{tournament_id}")
    assert tournament_page.status_code == 200
    assert "Arena Night" in tournament_page.text

    game_page = client.get(f"/games/{game_id}")
    assert game_page.status_code == 200
    assert "Move List" in game_page.text
    assert "Seat State" in game_page.text
