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
    color TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
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

SCHEMA_STATEMENTS = (
    GAME_TABLE_SQL,
    TURN_TABLE_SQL,
    HALLUCINATION_TABLE_SQL,
    TURNS_GAME_INDEX_SQL,
    HALLUCINATIONS_GAME_INDEX_SQL,
)
