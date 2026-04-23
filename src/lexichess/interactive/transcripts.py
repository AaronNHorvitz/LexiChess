from __future__ import annotations

from typing import Any


def build_referee_ruling(
    *,
    color: str,
    reason: str,
    detail: str,
    move_text: str | None = None,
) -> dict[str, Any]:
    attempted = f" after {move_text!r}" if move_text else ""
    return {
        "role": "referee",
        "speaker": "Gemma 4 Referee",
        "category": "ruling",
        "target": color,
        "message": (
            f"Ref's whistle on {color}{attempted}: {detail} "
            "Reset, breathe, and submit one legal SAN move."
        ),
        "reason": reason,
    }


def build_referee_provider_error(
    *,
    color: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "role": "referee",
        "speaker": "Gemma 4 Referee",
        "category": "system",
        "target": color,
        "message": (
            f"Timeout in the booth for {color}. The engine room coughed, the move never arrived, "
            "and the game has to be called by rule."
        ),
        "reason": "provider_error",
        "detail": detail,
    }


def build_referee_finish(
    *,
    result: str | None,
    termination_reason: str | None,
) -> dict[str, Any]:
    reason = termination_reason or "game_over"
    final_call = "Decision pending."
    if result == "1-0":
        final_call = "White takes it."
    elif result == "0-1":
        final_call = "Black takes it."
    elif result == "1/2-1/2":
        final_call = "Nobody could pry it open. Draw."

    if termination_reason and "checkmate" in termination_reason:
        final_call += " GOOOOOAAAAAAALL and CHECKMATE!"

    return {
        "role": "referee",
        "speaker": "Gemma 4 Referee",
        "category": "finish",
        "message": f"{final_call} Official ruling: {reason}.",
        "result": result,
        "termination_reason": reason,
    }


def build_player_banter(
    *,
    color: str,
    speaker: str,
    move: str,
) -> dict[str, Any]:
    choices = (
        f"{speaker} slams down {move} and starts grinning at the other side of the board.",
        f"{speaker} plays {move} like it was obvious and waits for somebody to complain.",
        f"{speaker} drops {move} with the confidence of somebody who absolutely wants a reaction.",
        f"{speaker} fires in {move} and immediately starts talking like the scoreboard already agrees.",
    )
    index = sum(ord(char) for char in f"{color}:{speaker}:{move}") % len(choices)
    return {
        "role": "player",
        "speaker": speaker,
        "category": "banter",
        "target": "opponent",
        "message": choices[index],
        "move": move,
        "color": color,
    }


def build_finish_banter(
    *,
    winner: str | None,
    result: str | None,
) -> dict[str, Any] | None:
    if result == "1/2-1/2" or winner is None:
        return None
    return {
        "role": "player",
        "speaker": winner,
        "category": "finish",
        "target": "crowd",
        "message": f"{winner} starts celebrating like the whole arena heard that last move coming.",
        "result": result,
    }
