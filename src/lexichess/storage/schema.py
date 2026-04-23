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
    mode TEXT NOT NULL DEFAULT 'benchmark',
    status TEXT NOT NULL,
    result TEXT,
    termination_reason TEXT
);
"""

GAME_SEAT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS game_seats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    color TEXT NOT NULL,
    controller TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    display_name TEXT,
    claimed_by TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_id, color)
);
"""

GAME_EVENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS game_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    color TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

ENGINE_ANALYSIS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS engine_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    turn_id INTEGER REFERENCES turns(id) ON DELETE SET NULL,
    ply INTEGER NOT NULL,
    analyzed_fen TEXT NOT NULL,
    engine_path TEXT NOT NULL,
    engine_depth INTEGER,
    engine_multipv INTEGER,
    engine_movetime_ms INTEGER,
    multipv_rank INTEGER NOT NULL,
    best_move_uci TEXT,
    best_move_san TEXT,
    score_cp INTEGER,
    score_mate INTEGER,
    pv_uci_json TEXT NOT NULL,
    pv_san_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

TOURNAMENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    format TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    config_json TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);
"""

TOURNAMENT_PLAYER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tournament_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    seed INTEGER,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    display_name TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

TOURNAMENT_PAIRING_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tournament_pairings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
    match_number INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    white_player_id INTEGER NOT NULL REFERENCES tournament_players(id) ON DELETE CASCADE,
    black_player_id INTEGER NOT NULL REFERENCES tournament_players(id) ON DELETE CASCADE,
    tag TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    game_id INTEGER REFERENCES games(id) ON DELETE SET NULL,
    result TEXT,
    termination_reason TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    completed_at TEXT
);
"""

TURNS_GAME_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_turns_game_id ON turns(game_id);
"""

GAME_SEATS_GAME_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_game_seats_game_id
ON game_seats(game_id, color ASC, id ASC);
"""

GAME_EVENTS_GAME_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_game_events_game_id
ON game_events(game_id, id ASC);
"""

HALLUCINATIONS_GAME_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_hallucinations_game_id ON hallucinations(game_id);
"""

ENGINE_ANALYSES_GAME_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_engine_analyses_game_id
ON engine_analyses(game_id, ply ASC, multipv_rank ASC, id ASC);
"""

ENGINE_ANALYSES_TURN_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_engine_analyses_turn_id ON engine_analyses(turn_id);
"""

TOURNAMENT_STATUS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status, id DESC);
"""

TOURNAMENT_PLAYERS_TOURNAMENT_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_tournament_players_tournament_id
ON tournament_players(tournament_id, seed ASC, id ASC);
"""

TOURNAMENT_PAIRINGS_TOURNAMENT_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_tournament_pairings_tournament_id
ON tournament_pairings(tournament_id, match_number ASC, id ASC);
"""

TOURNAMENT_PAIRINGS_STATUS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_tournament_pairings_status
ON tournament_pairings(tournament_id, status, match_number ASC, id ASC);
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
    competitor_result TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

RATINGS_SLUG_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_ratings_competitor_slug ON ratings(competitor_slug, id DESC);
"""

BASE_SCHEMA_STATEMENTS = (
    GAME_TABLE_SQL,
    GAME_SEAT_TABLE_SQL,
    GAME_EVENT_TABLE_SQL,
    TURN_TABLE_SQL,
    HALLUCINATION_TABLE_SQL,
    ENGINE_ANALYSIS_TABLE_SQL,
    TOURNAMENT_TABLE_SQL,
    TOURNAMENT_PLAYER_TABLE_SQL,
    TOURNAMENT_PAIRING_TABLE_SQL,
    RATINGS_TABLE_SQL,
    TURNS_GAME_INDEX_SQL,
    GAME_SEATS_GAME_INDEX_SQL,
    GAME_EVENTS_GAME_INDEX_SQL,
    HALLUCINATIONS_GAME_INDEX_SQL,
    ENGINE_ANALYSES_GAME_INDEX_SQL,
    ENGINE_ANALYSES_TURN_INDEX_SQL,
    TOURNAMENT_STATUS_INDEX_SQL,
    TOURNAMENT_PLAYERS_TOURNAMENT_INDEX_SQL,
    TOURNAMENT_PAIRINGS_TOURNAMENT_INDEX_SQL,
    TOURNAMENT_PAIRINGS_STATUS_INDEX_SQL,
    RATINGS_SLUG_INDEX_SQL,
)

GAME_MIGRATION_COLUMNS = {
    "mode": "TEXT NOT NULL DEFAULT 'benchmark'",
}

TURN_MIGRATION_COLUMNS = {
    "attempt": "INTEGER NOT NULL DEFAULT 1",
    "prompt_kind": "TEXT NOT NULL DEFAULT 'benchmark_move'",
    "prompt_version": "TEXT NOT NULL DEFAULT 'benchmark_move.v1'",
    "deterministic_explanation": "TEXT",
    "referee_note": "TEXT",
}

RATING_MIGRATION_COLUMNS = {
    "competitor_result": "TEXT",
}


def ensure_schema(connection: sqlite3.Connection) -> None:
    for statement in BASE_SCHEMA_STATEMENTS:
        connection.execute(statement)

    for column_name, column_sql in GAME_MIGRATION_COLUMNS.items():
        _ensure_column(connection, "games", column_name, column_sql)

    for column_name, column_sql in TURN_MIGRATION_COLUMNS.items():
        _ensure_column(connection, "turns", column_name, column_sql)

    for column_name, column_sql in RATING_MIGRATION_COLUMNS.items():
        _ensure_column(connection, "ratings", column_name, column_sql)


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
