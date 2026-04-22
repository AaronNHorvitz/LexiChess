from lexichess.chess import ChessBoard


def test_board_applies_san_and_tracks_history() -> None:
    board = ChessBoard()

    assert board.turn_color == "white"
    assert board.apply_san("e4") == "e4"
    assert board.turn_color == "black"
    assert board.move_history_san() == ["e4"]
