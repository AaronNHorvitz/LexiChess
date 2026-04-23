from __future__ import annotations

import json
from pathlib import Path

from lexichess.chess import ChessBoard


def test_board_applies_san_and_tracks_history() -> None:
    board = ChessBoard()

    assert board.turn_color == "white"
    assert board.apply_san("e4") == "e4"
    assert board.turn_color == "black"
    assert board.move_history_san() == ["e4"]


def test_board_exports_pgn_for_non_starting_position() -> None:
    board = ChessBoard("8/P7/8/8/8/8/8/k6K w - - 0 1")
    board.apply_san("a8=Q+")

    pgn = board.export_pgn(headers={"White": "tester", "Black": "engine"})

    assert '[SetUp "1"]' in pgn
    assert '[FEN "8/P7/8/8/8/8/8/k6K w - - 0 1"]' in pgn
    assert "1. a8=Q+" in pgn


def test_board_describes_invalid_move_with_legal_examples() -> None:
    board = ChessBoard()
    interpretation = board.parse_move_text("banana")

    explanation = board.describe_interpretation_failure(interpretation)

    assert "No recognizable SAN or UCI move was found" in explanation


def test_board_regression_positions_from_fixture_corpus() -> None:
    fixture_path = Path(__file__).with_name("fixtures") / "edge_positions.json"
    fixtures = json.loads(fixture_path.read_text())

    for fixture in fixtures:
        board = ChessBoard(fixture["fen"])
        assert board.apply_san(fixture["san"]) == fixture["san"]
