from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from lexichess.chess import ChessBoard


def accepted_turns(turns: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    for turn in turns:
        if turn.get("is_legal") and turn.get("parsed_move_san"):
            accepted.append(dict(turn))
    return accepted


def accepted_san_moves(turns: Iterable[Mapping[str, Any]]) -> list[str]:
    return [
        str(turn["parsed_move_san"])
        for turn in accepted_turns(turns)
        if turn.get("parsed_move_san")
    ]


def render_move_list(turns: Iterable[Mapping[str, Any]]) -> str:
    moves = accepted_san_moves(turns)
    if not moves:
        return "No legal moves recorded."

    lines: list[str] = []
    for index in range(0, len(moves), 2):
        move_number = index // 2 + 1
        white_move = moves[index]
        black_move = moves[index + 1] if index + 1 < len(moves) else ""
        line = f"{move_number}. {white_move}"
        if black_move:
            line += f" {black_move}"
        lines.append(line)
    return "\n".join(lines)


def build_game_pgn(
    game: Mapping[str, Any],
    turns: Iterable[Mapping[str, Any]],
) -> str:
    board = ChessBoard(str(game["initial_fen"]))
    board.apply_moves_san(accepted_san_moves(turns))
    headers = {
        "Event": "LexiChess Match",
        "White": f"{game['white_provider']}:{game['white_model']}",
        "Black": f"{game['black_provider']}:{game['black_model']}",
        "Result": str(game.get("result") or "*"),
        "Termination": game.get("termination_reason"),
    }
    return board.export_pgn(headers=headers)


def build_game_bundle(
    game: Mapping[str, Any],
    turns: Iterable[Mapping[str, Any]],
    hallucinations: Iterable[Mapping[str, Any]],
    engine_analyses: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    turn_rows = [dict(turn) for turn in turns]
    hallucination_rows = [dict(item) for item in hallucinations]
    analysis_rows = [dict(item) for item in (engine_analyses or ())]
    accepted = accepted_turns(turn_rows)
    return {
        "game": dict(game),
        "turns": turn_rows,
        "accepted_turns": accepted,
        "moves": accepted_san_moves(accepted),
        "hallucinations": hallucination_rows,
        "engine_analyses": analysis_rows,
        "move_list": render_move_list(accepted),
        "pgn": build_game_pgn(game, accepted),
    }


def export_game_json(
    game: Mapping[str, Any],
    turns: Iterable[Mapping[str, Any]],
    hallucinations: Iterable[Mapping[str, Any]],
    engine_analyses: Iterable[Mapping[str, Any]] | None = None,
) -> str:
    return json.dumps(
        build_game_bundle(game, turns, hallucinations, engine_analyses),
        indent=2,
    )
