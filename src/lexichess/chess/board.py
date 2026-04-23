from __future__ import annotations

from collections.abc import Iterable, Mapping

import chess
import chess.pgn

from lexichess.chess.parsing import MoveInterpretation, interpret_move_text


class ChessBoard:
    def __init__(self, fen: str | None = None) -> None:
        self._initial_fen = fen or chess.STARTING_FEN
        self._board = chess.Board(fen) if fen else chess.Board()

    @property
    def fen(self) -> str:
        return self._board.fen()

    @property
    def initial_fen(self) -> str:
        return self._initial_fen

    @property
    def ply(self) -> int:
        return len(self._board.move_stack) + 1

    @property
    def turn_color(self) -> str:
        return "white" if self._board.turn == chess.WHITE else "black"

    def legal_moves_san(self) -> list[str]:
        return sorted(self._board.san(move) for move in self._board.legal_moves)

    def legal_moves_preview(self, limit: int = 10) -> tuple[str, ...]:
        return tuple(self.legal_moves_san()[:limit])

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

    def apply_moves_san(self, moves: Iterable[str]) -> None:
        for san in moves:
            self.apply_san(san)

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

    def describe_interpretation_failure(
        self, interpretation: MoveInterpretation, *, preview_limit: int = 10
    ) -> str:
        preview = ", ".join(self.legal_moves_preview(limit=preview_limit))
        if interpretation.reason == "empty_response":
            return (
                "No move was provided. Submit exactly one legal SAN move in the form "
                "'MOVE: <SAN>'."
            )
        if interpretation.reason == "no_candidate_found":
            return (
                "No recognizable SAN or UCI move was found in the response. Submit "
                "exactly one legal SAN move in the form 'MOVE: <SAN>'."
            )

        candidate = interpretation.candidate or interpretation.raw_text.strip() or "?"
        return (
            f"{candidate!r} is not a legal move for {self.turn_color} in this "
            f"position. Submit exactly one legal SAN move. Legal examples: {preview}"
        )

    def export_pgn(self, *, headers: Mapping[str, str | None] | None = None) -> str:
        game = chess.pgn.Game()
        node: chess.pgn.GameNode = game
        for move in self._board.move_stack:
            node = node.add_variation(move)

        default_headers = {
            "Event": "LexiChess Match",
            "Result": self.result() or "*",
        }
        for key, value in {**default_headers, **(headers or {})}.items():
            if value is not None:
                game.headers[key] = value

        if self._initial_fen != chess.STARTING_FEN:
            game.headers["SetUp"] = "1"
            game.headers["FEN"] = self._initial_fen

        exporter = chess.pgn.StringExporter(
            headers=True,
            variations=False,
            comments=False,
        )
        return str(game.accept(exporter)).strip()
