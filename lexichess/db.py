import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable, Optional, Tuple


class Database:
    """Simple SQLite helper for storing games and conversations."""

    def __init__(self, path: str | Path = "lexichess.db") -> None:
        self.path = Path(path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT,
                    end_time TEXT,
                    result TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS moves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER,
                    move_number INTEGER,
                    player TEXT,
                    move TEXT,
                    is_valid INTEGER,
                    timestamp TEXT,
                    FOREIGN KEY(game_id) REFERENCES games(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id INTEGER,
                    player TEXT,
                    message TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(game_id) REFERENCES games(id)
                )
                """
            )

    def add_game(self, start_time: str) -> int:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                "INSERT INTO games (start_time) VALUES (?)",
                (start_time,),
            )
            return cur.lastrowid

    def end_game(self, game_id: int, end_time: str, result: str) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "UPDATE games SET end_time=?, result=? WHERE id=?",
                (end_time, result, game_id),
            )

    def add_move(
        self,
        game_id: int,
        move_number: int,
        player: str,
        move: str,
        is_valid: bool,
        timestamp: str,
    ) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """INSERT INTO moves (game_id, move_number, player, move, is_valid, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (game_id, move_number, player, move, int(is_valid), timestamp),
            )

    def add_conversation(
        self,
        game_id: int,
        player: str,
        message: str,
        timestamp: str,
    ) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO conversations (game_id, player, message, timestamp) VALUES (?, ?, ?, ?)",
                (game_id, player, message, timestamp),
            )

    def get_moves(self, game_id: int) -> Iterable[Tuple[int, str, str]]:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                "SELECT move_number, player, move FROM moves WHERE game_id=? ORDER BY move_number",
                (game_id,),
            )
            return cur.fetchall()

    def get_conversations(self, game_id: int) -> Iterable[Tuple[str, str]]:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                "SELECT player, message FROM conversations WHERE game_id=? ORDER BY id",
                (game_id,),
            )
            return cur.fetchall()
