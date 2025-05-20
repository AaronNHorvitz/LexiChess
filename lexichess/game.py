from __future__ import annotations

import random
import chess

from .db import Database
from .utils import now_iso
from .llm.base import BaseLLM


class LexiChessGame:
    """Orchestrate a chess match between two LLM players."""

    def __init__(self, white: BaseLLM, black: BaseLLM, db: Database | None = None):
        self.white = white
        self.black = black
        self.db = db or Database()

    def play(self) -> str:
        board = chess.Board()
        game_id = self.db.add_game(now_iso())
        move_number = 1
        history = ""
        while not board.is_game_over(claim_draw=True):
            player = self.white if board.turn == chess.WHITE else self.black
            player_name = "white" if board.turn == chess.WHITE else "black"
            move_str = player.generate_move(board, history)
            try:
                move = chess.Move.from_uci(move_str)
                is_valid = move in board.legal_moves
            except ValueError:
                is_valid = False
            if is_valid:
                board.push(move)
                history += f"{move_str} "
            else:
                # hallucination: choose random legal move
                move = random.choice(list(board.legal_moves))
                board.push(move)
                history += f"{move.uci()} "
            self.db.add_move(
                game_id, move_number, player_name, move_str, is_valid, now_iso()
            )
            move_number += 1

        result = board.result()
        self.db.end_game(game_id, now_iso(), result)
        return result
