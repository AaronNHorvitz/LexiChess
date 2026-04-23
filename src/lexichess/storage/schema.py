from __future__ import annotations

import sqlite3

GAME_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT,
    white_provider TEXT NOT NULL,
    white_model TEXT NOT NULL,
    black_provider TEXT NOT NULL,
    black_model TEXT NOT NULL,
    initial_fen TEXT NOT NULL,
    status TEXT NOT NULL,
    result TEXT,
    termination_reason TEXT
);
"""

TURN_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    ply INTEGER NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 1,
    color TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_kind TEXT NOT NULL DEFAULT 'benchmark_move',
    prompt_version TEXT NOT NULL DEFAULT 'benchmark_move.v1',
    prompt TEXT NOT NULL,
    instructions TEXT NOT NULL,
    raw_response_text TEXT NOT NULL,
    raw_response_json TEXT,
    candidate_move TEXT,
    parsed_move_san TEXT,
    parsed_move_uci TEXT,
    fen_before TEXT NOT NULL,
    fen_after TEXT,
    is_legal INTEGER NOT NULL,
    latency_ms INTEGER,
    error TEXT,
    deterministic_explanation TEXT,
    referee_note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

HALLUCINATION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS hallucinations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    turn_id INTEGER REFERENCES turns(id) ON DELETE SET NULL,
    color TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    raw_response_text TEXT NOT NULL,
    candidate_move TEXT,
    reason TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

TURNS_GAME_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_turns_game_id ON turns(game_id);
"""

HALLUCINATIONS_GAME_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_hallucinations_game_id ON hallucinations(game_id);
"""

RATINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_slug TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    runtime TEXT NOT NULL,
    prompt_profile TEXT NOT NULL,
    quantization TEXT,
    hardware_class TEXT,
    revision TEXT,
    rating REAL NOT NULL,
    games_played INTEGER NOT NULL,
    provisional INTEGER NOT NULL,
    source_game_id INTEGER REFERENCES games(id) ON DELETE SET NULL,
    source_result TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

RATINGS_SLUG_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_ratings_competitor_slug ON ratings(competitor_slug, id DESC);
"""

BASE_SCHEMA_STATEMENTS = (
    GAME_TABLE_SQL,
    TURN_TABLE_SQL,
    HALLUCINATION_TABLE_SQL,
    RATINGS_TABLE_SQL,
    TURNS_GAME_INDEX_SQL,
    HALLUCINATIONS_GAME_INDEX_SQL,
    RATINGS_SLUG_INDEX_SQL,
)

TURN_MIGRATION_COLUMNS = {
    "attempt": "INTEGER NOT NULL DEFAULT 1",
    "prompt_kind": "TEXT NOT NULL DEFAULT 'benchmark_move'",
    "prompt_version": "TEXT NOT NULL DEFAULT 'benchmark_move.v1'",
    "deterministic_explanation": "TEXT",
    "referee_note": "TEXT",
}


def ensure_schema(connection: sqlite3.Connection) -> None:
    for statement in BASE_SCHEMA_STATEMENTS:
        connection.execute(statement)

    for column_name, column_sql in TURN_MIGRATION_COLUMNS.items():
        _ensure_column(connection, "turns", column_name, column_sql)


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_sql: str,
) -> None:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing = {row[1] for row in rows}
    if column_name in existing:
        return
    connection.execute(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"
    )
