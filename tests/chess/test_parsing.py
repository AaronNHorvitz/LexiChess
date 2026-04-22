import chess

from lexichess.chess import interpret_move_text


def test_parsing_extracts_san_from_extra_text() -> None:
    board = chess.Board()

    interpretation = interpret_move_text(board, "I would play Nf3 here.")

    assert interpretation.san == "Nf3"
    assert interpretation.uci == "g1f3"


def test_parsing_accepts_uci_moves() -> None:
    board = chess.Board()

    interpretation = interpret_move_text(board, "move: e2e4")

    assert interpretation.san == "e4"
    assert interpretation.uci == "e2e4"


def test_parsing_reports_unusable_output() -> None:
    board = chess.Board()

    interpretation = interpret_move_text(board, "banana")

    assert interpretation.san is None
    assert interpretation.reason == "no_candidate_found"
