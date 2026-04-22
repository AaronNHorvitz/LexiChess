from __future__ import annotations

from typing import Iterable

import chess

from lexichess.chess.parsing import MoveInterpretation, interpret_move_text


class ChessBoard:
    def __init__(self, fen: str | None = None) -> None:
        self._initial_fen = fen or chess.STARTING_FEN
        self._board = chess.Board(fen) if fen else chess.Board()

    @property
    def fen(self) -> str:
        return self._board.fen()

    @property
    def ply(self) -> int:
        return len(self._board.move_stack) + 1

    @property
    def turn_color(self) -> str:
        return "white" if self._board.turn == chess.WHITE else "black"

    def legal_moves_san(self) -> list[str]:
        return sorted(self._board.san(move) for move in self._board.legal_moves)

    def move_history_san(self) -> list[str]:
        replay = chess.Board(self._initial_fen)
        history: list[str] = []
        for move in self._board.move_stack:
            history.append(replay.san(move))
            replay.push(move)
        return history

    def parse_move_text(self, text: str) -> MoveInterpretation:
        return interpret_move_text(self._board, text)

    def apply_san(self, san: str) -> str:
        move = self._board.parse_san(san)
        normalized = self._board.san(move)
        self._board.push(move)
        return normalized

    def is_game_over(self) -> bool:
        return self._board.is_game_over(claim_draw=True)

    def result(self) -> str | None:
        if not self.is_game_over():
            return None
        return self._board.result(claim_draw=True)

    def outcome_reason(self) -> str | None:
        outcome = self._board.outcome(claim_draw=True)
        if outcome is None:
            return None
        return outcome.termination.name.lower()

    def legal_moves_uci(self) -> Iterable[str]:
        return (move.uci() for move in self._board.legal_moves)
