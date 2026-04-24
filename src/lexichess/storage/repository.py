from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence as SequenceCollection
from pathlib import Path
from typing import Any, Mapping, Sequence

from lexichess.analysis import EngineAnalysis
from lexichess.index.models import RatingSnapshot
from lexichess.storage.schema import ensure_schema

DEFAULT_BROADCAST_ENABLED_SECTIONS = (
    "highlights",
    "quotes",
    "showmatch_feed",
    "audio_sync",
    "clips",
    "timeline",
)


class SQLiteRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            ensure_schema(connection)
            connection.commit()

    def create_game(
        self,
        *,
        white_provider: str,
        white_model: str,
        black_provider: str,
        black_model: str,
        initial_fen: str,
        mode: str = "benchmark",
        status: str = "running",
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO games (
                    white_provider,
                    white_model,
                    black_provider,
                    black_model,
                    initial_fen,
                    mode,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    white_provider,
                    white_model,
                    black_provider,
                    black_model,
                    initial_fen,
                    mode,
                    status,
                ),
            )
            connection.commit()
            return _lastrowid(cursor)

    def finish_game(
        self,
        game_id: int,
        *,
        status: str,
        result: str | None,
        termination_reason: str | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE games
                SET ended_at = CURRENT_TIMESTAMP,
                    status = ?,
                    result = ?,
                    termination_reason = ?
                WHERE id = ?
                """,
                (status, result, termination_reason, game_id),
            )
            connection.commit()

    def update_game_status(self, game_id: int, *, status: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE games
                SET status = ?
                WHERE id = ?
                """,
                (status, game_id),
            )
            connection.commit()

    def log_turn(
        self,
        *,
        game_id: int,
        ply: int,
        attempt: int = 1,
        color: str,
        provider: str,
        model: str,
        prompt_kind: str = "benchmark_move",
        prompt_version: str = "benchmark_move.v1",
        prompt: str,
        instructions: str,
        raw_response_text: str,
        raw_response_json: dict[str, Any] | None,
        candidate_move: str | None,
        parsed_move_san: str | None,
        parsed_move_uci: str | None,
        fen_before: str,
        fen_after: str | None,
        is_legal: bool,
        latency_ms: int | None,
        error: str | None,
        deterministic_explanation: str | None = None,
        referee_note: str | None = None,
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO turns (
                    game_id,
                    ply,
                    attempt,
                    color,
                    provider,
                    model,
                    prompt_kind,
                    prompt_version,
                    prompt,
                    instructions,
                    raw_response_text,
                    raw_response_json,
                    candidate_move,
                    parsed_move_san,
                    parsed_move_uci,
                    fen_before,
                    fen_after,
                    is_legal,
                    latency_ms,
                    error,
                    deterministic_explanation,
                    referee_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    ply,
                    attempt,
                    color,
                    provider,
                    model,
                    prompt_kind,
                    prompt_version,
                    prompt,
                    instructions,
                    raw_response_text,
                    _dump_json(raw_response_json),
                    candidate_move,
                    parsed_move_san,
                    parsed_move_uci,
                    fen_before,
                    fen_after,
                    1 if is_legal else 0,
                    latency_ms,
                    error,
                    deterministic_explanation,
                    referee_note,
                ),
            )
            connection.commit()
            return _lastrowid(cursor)

    def log_hallucination(
        self,
        *,
        game_id: int,
        turn_id: int | None,
        color: str,
        provider: str,
        model: str,
        raw_response_text: str,
        candidate_move: str | None,
        reason: str,
        details: str | None = None,
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO hallucinations (
                    game_id,
                    turn_id,
                    color,
                    provider,
                    model,
                    raw_response_text,
                    candidate_move,
                    reason,
                    details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    turn_id,
                    color,
                    provider,
                    model,
                    raw_response_text,
                    candidate_move,
                    reason,
                    details,
                ),
            )
            connection.commit()
            return _lastrowid(cursor)

    def get_game(self, game_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM games WHERE id = ?",
                (game_id,),
            ).fetchone()
        return _game_row(row) if row else None

    def list_games(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM games ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_game_row(row) for row in rows]

    def upsert_game_seat(
        self,
        *,
        game_id: int,
        color: str,
        controller: str,
        provider: str | None,
        model: str | None,
        display_name: str | None,
        claimed_by: str | None,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO game_seats (
                    game_id,
                    color,
                    controller,
                    provider,
                    model,
                    display_name,
                    claimed_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id, color)
                DO UPDATE SET
                    controller = excluded.controller,
                    provider = COALESCE(excluded.provider, game_seats.provider),
                    model = COALESCE(excluded.model, game_seats.model),
                    display_name = COALESCE(excluded.display_name, game_seats.display_name),
                    claimed_by = excluded.claimed_by,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    game_id,
                    color,
                    controller,
                    provider,
                    model,
                    display_name,
                    claimed_by,
                ),
            )
            connection.commit()

        seat = self.get_game_seat(game_id, color)
        if seat is None:
            raise RuntimeError("Seat upsert did not persist a row.")
        return seat

    def get_game_seat(self, game_id: int, color: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM game_seats
                WHERE game_id = ? AND color = ?
                """,
                (game_id, color),
            ).fetchone()
        return _game_seat_row(row) if row else None

    def list_game_seats(self, game_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM game_seats
                WHERE game_id = ?
                ORDER BY CASE color WHEN 'white' THEN 0 WHEN 'black' THEN 1 ELSE 2 END,
                         id ASC
                """,
                (game_id,),
            ).fetchall()
        return [_game_seat_row(row) for row in rows]

    def log_game_event(
        self,
        *,
        game_id: int,
        event_type: str,
        payload: dict[str, Any],
        color: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO game_events (
                    game_id,
                    event_type,
                    color,
                    payload_json
                ) VALUES (?, ?, ?, ?)
                """,
                (game_id, event_type, color, _dump_json(payload)),
            )
            connection.commit()
            event_id = _lastrowid(cursor)

            row = connection.execute(
                """
                SELECT * FROM game_events
                WHERE id = ?
                """,
                (event_id,),
            ).fetchone()

        if row is None:
            raise RuntimeError("Game event insert did not persist a row.")
        return _game_event_row(row)

    def list_game_events(
        self,
        game_id: int,
        *,
        after_id: int | None = None,
        event_types: SequenceCollection[str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        where_parts = ["game_id = ?"]
        params: list[Any] = [game_id]
        if after_id is not None:
            where_parts.append("id > ?")
            params.append(after_id)
        if event_types:
            placeholders = ", ".join("?" for _ in event_types)
            where_parts.append(f"event_type IN ({placeholders})")
            params.extend(event_types)
        params.append(limit)
        where_clause = " AND ".join(where_parts)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM game_events
                WHERE {where_clause}
                ORDER BY id ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [_game_event_row(row) for row in rows]

    def latest_game_event(self, game_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM game_events
                WHERE game_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (game_id,),
            ).fetchone()
        return _game_event_row(row) if row else None

    def list_turns(
        self, game_id: int, *, legal_only: bool = False
    ) -> list[dict[str, Any]]:
        where_clause = "WHERE game_id = ?"
        params: tuple[Any, ...] = (game_id,)
        if legal_only:
            where_clause += " AND is_legal = 1"
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM turns
                {where_clause}
                ORDER BY ply ASC, attempt ASC, id ASC
                """,
                params,
            ).fetchall()
        return [_turn_row(row) for row in rows]

    def list_hallucinations(self, game_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM hallucinations WHERE game_id = ? ORDER BY id ASC",
                (game_id,),
            ).fetchall()
        return [_plain_row(row) for row in rows]

    def log_engine_analysis(
        self,
        *,
        game_id: int,
        turn_id: int | None,
        ply: int,
        analyzed_fen: str,
        engine_path: str,
        engine_depth: int | None,
        engine_multipv: int | None,
        engine_movetime_ms: int | None,
        lines: list[EngineAnalysis],
    ) -> None:
        if not lines:
            return

        rows = [
            (
                game_id,
                turn_id,
                ply,
                analyzed_fen,
                engine_path,
                engine_depth,
                engine_multipv,
                engine_movetime_ms,
                line.multipv_rank,
                line.best_move_uci,
                line.best_move_san,
                line.score_cp,
                line.score_mate,
                _dump_json({"pv_uci": list(line.pv_uci)}),
                _dump_json({"pv_san": list(line.pv_san)}),
            )
            for line in lines
        ]

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO engine_analyses (
                    game_id,
                    turn_id,
                    ply,
                    analyzed_fen,
                    engine_path,
                    engine_depth,
                    engine_multipv,
                    engine_movetime_ms,
                    multipv_rank,
                    best_move_uci,
                    best_move_san,
                    score_cp,
                    score_mate,
                    pv_uci_json,
                    pv_san_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            connection.commit()

    def list_engine_analyses(
        self,
        game_id: int,
        *,
        ply: int | None = None,
    ) -> list[dict[str, Any]]:
        where_clause = "WHERE game_id = ?"
        params: tuple[Any, ...] = (game_id,)
        if ply is not None:
            where_clause += " AND ply = ?"
            params = (game_id, ply)

        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM engine_analyses
                {where_clause}
                ORDER BY ply ASC, multipv_rank ASC, id ASC
                """,
                params,
            ).fetchall()
        return [_engine_analysis_row(row) for row in rows]

    def create_tournament(
        self,
        *,
        name: str,
        tournament_format: str,
        status: str = "created",
        config: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tournaments (
                    name,
                    format,
                    status,
                    config_json,
                    notes
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    name,
                    tournament_format,
                    status,
                    _dump_json(config),
                    notes,
                ),
            )
            connection.commit()
            return _lastrowid(cursor)

    def get_tournament(self, tournament_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tournaments WHERE id = ?",
                (tournament_id,),
            ).fetchone()
        return _tournament_row(row) if row else None

    def list_tournaments(
        self,
        *,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        where_clause = ""
        params: tuple[Any, ...] = (limit,)
        if status is not None:
            where_clause = "WHERE status = ?"
            params = (status, limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM tournaments
                {where_clause}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [_tournament_row(row) for row in rows]

    def update_tournament_status(self, tournament_id: int, *, status: str) -> None:
        started_at_sql = (
            ", started_at = COALESCE(started_at, CURRENT_TIMESTAMP)"
            if status == "running"
            else ""
        )
        completed_at_sql = (
            ", completed_at = CURRENT_TIMESTAMP" if status == "completed" else ""
        )
        with self._connect() as connection:
            connection.execute(
                f"""
                UPDATE tournaments
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP
                    {started_at_sql}
                    {completed_at_sql}
                WHERE id = ?
                """,
                (status, tournament_id),
            )
            connection.commit()

    def add_tournament_player(
        self,
        tournament_id: int,
        *,
        provider: str,
        model: str,
        display_name: str | None = None,
        seed: int | None = None,
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tournament_players (
                    tournament_id,
                    seed,
                    provider,
                    model,
                    display_name
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (tournament_id, seed, provider, model, display_name),
            )
            connection.commit()
            return _lastrowid(cursor)

    def list_tournament_players(self, tournament_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM tournament_players
                WHERE tournament_id = ?
                ORDER BY seed ASC, id ASC
                """,
                (tournament_id,),
            ).fetchall()
        return [_tournament_player_row(row) for row in rows]

    def create_tournament_pairings(
        self,
        tournament_id: int,
        pairings: Sequence[Mapping[str, Any]],
    ) -> None:
        if not pairings:
            return
        rows = [
            (
                tournament_id,
                int(pairing["match_number"]),
                int(pairing["round_number"]),
                int(pairing["white_player_id"]),
                int(pairing["black_player_id"]),
                pairing.get("tag"),
                pairing.get("status", "pending"),
            )
            for pairing in pairings
        ]
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO tournament_pairings (
                    tournament_id,
                    match_number,
                    round_number,
                    white_player_id,
                    black_player_id,
                    tag,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            connection.commit()

    def get_tournament_pairing(self, pairing_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                _TOURNAMENT_PAIRINGS_SELECT + " WHERE tp.id = ?",
                (pairing_id,),
            ).fetchone()
        return _tournament_pairing_row(row) if row else None

    def list_tournament_pairings(
        self,
        tournament_id: int,
        *,
        statuses: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        where_parts = ["tp.tournament_id = ?"]
        params: list[Any] = [tournament_id]
        if statuses:
            placeholders = ", ".join("?" for _ in statuses)
            where_parts.append(f"tp.status IN ({placeholders})")
            params.extend(statuses)
        where_clause = " AND ".join(where_parts)
        with self._connect() as connection:
            rows = connection.execute(
                _TOURNAMENT_PAIRINGS_SELECT
                + f" WHERE {where_clause} ORDER BY tp.match_number ASC, tp.id ASC",
                tuple(params),
            ).fetchall()
        return [_tournament_pairing_row(row) for row in rows]

    def start_tournament_pairing(self, pairing_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE tournament_pairings
                SET status = 'running',
                    error_message = NULL,
                    started_at = COALESCE(started_at, CURRENT_TIMESTAMP)
                WHERE id = ?
                """,
                (pairing_id,),
            )
            connection.commit()

    def finish_tournament_pairing(
        self,
        pairing_id: int,
        *,
        status: str,
        game_id: int | None,
        result: str | None,
        termination_reason: str | None,
        error_message: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE tournament_pairings
                SET status = ?,
                    game_id = ?,
                    result = ?,
                    termination_reason = ?,
                    error_message = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    status,
                    game_id,
                    result,
                    termination_reason,
                    error_message,
                    pairing_id,
                ),
            )
            connection.commit()

    def pause_tournament_pairing(
        self,
        pairing_id: int,
        *,
        error_message: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE tournament_pairings
                SET status = 'failed',
                    error_message = ?
                WHERE id = ?
                """,
                (error_message, pairing_id),
            )
            connection.commit()

    def compute_tournament_standings(
        self,
        tournament_id: int,
    ) -> list[dict[str, Any]]:
        players = self.list_tournament_players(tournament_id)
        pairings = self.list_tournament_pairings(tournament_id)
        standings: dict[int, dict[str, Any]] = {}
        for player in players:
            player_id = int(player["id"])
            standings[player_id] = {
                "player_id": player_id,
                "seed": player["seed"],
                "provider": player["provider"],
                "model": player["model"],
                "display_name": player["display_name"],
                "label": player["label"],
                "games_played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "points": 0.0,
            }

        for pairing in pairings:
            if pairing["status"] != "completed":
                continue
            result = pairing.get("result")
            if result not in {"1-0", "0-1", "1/2-1/2"}:
                continue

            white_id = int(pairing["white_player_id"])
            black_id = int(pairing["black_player_id"])
            white_row = standings[white_id]
            black_row = standings[black_id]
            white_row["games_played"] += 1
            black_row["games_played"] += 1

            if result == "1-0":
                white_row["wins"] += 1
                white_row["points"] += 1.0
                black_row["losses"] += 1
            elif result == "0-1":
                black_row["wins"] += 1
                black_row["points"] += 1.0
                white_row["losses"] += 1
            else:
                white_row["draws"] += 1
                black_row["draws"] += 1
                white_row["points"] += 0.5
                black_row["points"] += 0.5

        ordered = sorted(
            standings.values(),
            key=lambda row: (
                -float(row["points"]),
                -int(row["wins"]),
                int(row["seed"]) if row["seed"] is not None else 10_000,
                str(row["label"]),
            ),
        )
        for index, row in enumerate(ordered, start=1):
            row["rank"] = index
        return ordered

    def record_rating_snapshot(
        self,
        snapshot: RatingSnapshot,
        *,
        source_game_id: int | None = None,
        source_result: str | None = None,
        competitor_result: str | None = None,
    ) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO ratings (
                    competitor_slug,
                    provider,
                    model,
                    runtime,
                    prompt_profile,
                    quantization,
                    hardware_class,
                    revision,
                    rating,
                    games_played,
                    provisional,
                    source_game_id,
                    source_result,
                    competitor_result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.competitor.slug,
                    snapshot.competitor.provider,
                    snapshot.competitor.model,
                    snapshot.competitor.runtime,
                    snapshot.competitor.prompt_profile,
                    snapshot.competitor.quantization,
                    snapshot.competitor.hardware_class,
                    snapshot.competitor.revision,
                    snapshot.rating,
                    snapshot.games_played,
                    1 if snapshot.provisional else 0,
                    source_game_id,
                    source_result,
                    competitor_result,
                ),
            )
            connection.commit()
            return _lastrowid(cursor)

    def list_rating_snapshots_for_game(self, game_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM ratings
                WHERE source_game_id = ?
                ORDER BY id ASC
                """,
                (game_id,),
            ).fetchall()
        return [_rating_row(row) for row in rows]

    def latest_rating_snapshot(self, competitor_slug: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM ratings
                WHERE competitor_slug = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (competitor_slug,),
            ).fetchone()
        return _rating_row(row) if row else None

    def list_rating_history(self, competitor_slug: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM ratings
                WHERE competitor_slug = ?
                ORDER BY id ASC
                """,
                (competitor_slug,),
            ).fetchall()
        return [_rating_row(row) for row in rows]

    def list_latest_ratings(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT r.*
                FROM ratings r
                JOIN (
                    SELECT competitor_slug, MAX(id) AS latest_id
                    FROM ratings
                    GROUP BY competitor_slug
                ) latest
                ON r.id = latest.latest_id
                ORDER BY r.rating DESC, r.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_rating_row(row) for row in rows]

    def get_broadcast_controls(self) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM broadcast_controls
                WHERE id = 1
                """
            ).fetchone()
            if row is None:
                connection.execute(
                    """
                    INSERT INTO broadcast_controls (
                        id,
                        featured_game_id,
                        featured_clip_id,
                        enabled_sections_json
                    ) VALUES (1, NULL, NULL, ?)
                    """,
                    (
                        _dump_json(
                            {
                                "enabled_sections": list(
                                    DEFAULT_BROADCAST_ENABLED_SECTIONS
                                )
                            }
                        ),
                    ),
                )
                connection.commit()
                row = connection.execute(
                    """
                    SELECT * FROM broadcast_controls
                    WHERE id = 1
                    """
                ).fetchone()
        if row is None:
            raise RuntimeError("Broadcast controls row was not created.")
        return _broadcast_controls_row(row)

    def set_featured_showmatch(
        self,
        *,
        featured_game_id: int | None,
    ) -> dict[str, Any]:
        current = self.get_broadcast_controls()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE broadcast_controls
                SET featured_game_id = ?,
                    featured_clip_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                (
                    featured_game_id,
                    (
                        None
                        if current.get("featured_game_id") != featured_game_id
                        else current.get("featured_clip_id")
                    ),
                ),
            )
            connection.commit()
        return self.get_broadcast_controls()

    def set_featured_clip(self, *, featured_clip_id: str | None) -> dict[str, Any]:
        self.get_broadcast_controls()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE broadcast_controls
                SET featured_clip_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                (featured_clip_id,),
            )
            connection.commit()
        return self.get_broadcast_controls()

    def set_broadcast_enabled_sections(
        self,
        enabled_sections: Sequence[str],
    ) -> dict[str, Any]:
        unique_sections: list[str] = []
        for section in enabled_sections:
            normalized = str(section).strip()
            if normalized and normalized not in unique_sections:
                unique_sections.append(normalized)
        if not unique_sections:
            unique_sections = list(DEFAULT_BROADCAST_ENABLED_SECTIONS)
        self.get_broadcast_controls()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE broadcast_controls
                SET enabled_sections_json = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                (_dump_json({"enabled_sections": unique_sections}),),
            )
            connection.commit()
        return self.get_broadcast_controls()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _dump_json(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, sort_keys=True)


def _load_json(payload: str | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    return json.loads(payload)


def _plain_row(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _game_row(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _game_seat_row(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _game_event_row(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["payload_json"] = _load_json(payload["payload_json"])
    return payload


def _tournament_row(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["config_json"] = _load_json(payload["config_json"])
    return payload


def _tournament_player_row(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["label"] = payload["display_name"] or (
        f"{payload['provider']}:{payload['model']}"
    )
    return payload


def _tournament_pairing_row(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _turn_row(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["is_legal"] = bool(payload["is_legal"])
    payload["raw_response_json"] = _load_json(payload["raw_response_json"])
    return payload


def _engine_analysis_row(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    pv_uci_payload = _load_json(payload.pop("pv_uci_json"))
    pv_san_payload = _load_json(payload.pop("pv_san_json"))
    payload["pv_uci"] = (
        list(pv_uci_payload.get("pv_uci", [])) if pv_uci_payload is not None else []
    )
    payload["pv_san"] = (
        list(pv_san_payload.get("pv_san", [])) if pv_san_payload is not None else []
    )
    return payload


def _rating_row(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["provisional"] = bool(payload["provisional"])
    return payload


def _broadcast_controls_row(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    enabled_sections_payload = _load_json(payload.pop("enabled_sections_json"))
    payload["enabled_sections"] = (
        list(enabled_sections_payload.get("enabled_sections", []))
        if enabled_sections_payload is not None
        else list(DEFAULT_BROADCAST_ENABLED_SECTIONS)
    )
    return payload


def _lastrowid(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise RuntimeError("SQLite insert did not return a row id.")
    return int(cursor.lastrowid)


_TOURNAMENT_PAIRINGS_SELECT = """
SELECT
    tp.*,
    wp.seed AS white_seed,
    wp.provider AS white_provider,
    wp.model AS white_model,
    wp.display_name AS white_display_name,
    COALESCE(wp.display_name, wp.provider || ':' || wp.model) AS white_label,
    bp.seed AS black_seed,
    bp.provider AS black_provider,
    bp.model AS black_model,
    bp.display_name AS black_display_name,
    COALESCE(bp.display_name, bp.provider || ':' || bp.model) AS black_label
FROM tournament_pairings tp
JOIN tournament_players wp ON wp.id = tp.white_player_id
JOIN tournament_players bp ON bp.id = tp.black_player_id
"""
