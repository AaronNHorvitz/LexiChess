from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from lexichess.storage.schema import ensure_schema


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
                    status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    white_provider,
                    white_model,
                    black_provider,
                    black_model,
                    initial_fen,
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


def _turn_row(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["is_legal"] = bool(payload["is_legal"])
    payload["raw_response_json"] = _load_json(payload["raw_response_json"])
    return payload


def _lastrowid(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise RuntimeError("SQLite insert did not return a row id.")
    return int(cursor.lastrowid)
