from __future__ import annotations

from typing import Any


def build_referee_ruling(
    *,
    color: str,
    reason: str,
    detail: str,
    move_text: str | None = None,
    speaker_name: str = "Gemma 4 Referee",
) -> dict[str, Any]:
    attempted = f" after {move_text!r}" if move_text else ""
    return {
        "role": "referee",
        "speaker": speaker_name,
        "category": "ruling",
        "target": color,
        "message": (
            f"Ref's whistle on {color}{attempted}: {detail} "
            "Reset, breathe, and submit one legal SAN move."
        ),
        "reason": reason,
        "detail": detail,
        "coaching_suggestion": "Reset, breathe, and submit one legal SAN move.",
    }


def build_referee_provider_error(
    *,
    color: str,
    detail: str,
    speaker_name: str = "Gemma 4 Referee",
) -> dict[str, Any]:
    return {
        "role": "referee",
        "speaker": speaker_name,
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
    speaker_name: str = "Gemma 4 Referee",
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
        "speaker": speaker_name,
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


def build_showmatch_intro(
    *,
    speaker_name: str,
    white_player: str,
    black_player: str,
) -> dict[str, Any]:
    return {
        "role": "showmatch",
        "speaker": speaker_name,
        "category": "pregame",
        "target": "crowd",
        "message": (
            f"Welcome to the nonsense: {white_player} vs {black_player}. "
            "Keep the moves legal and the trash talk television-ready."
        ),
        "white_player": white_player,
        "black_player": black_player,
    }


def build_showmatch_hype(
    *,
    speaker_name: str,
    color: str,
    speaker: str,
    opponent: str | None,
    move: str,
    ply: int,
    tags: tuple[str, ...],
) -> dict[str, Any]:
    tag_text = ", ".join(tags) if tags else "pressure"
    choices = (
        f"{speaker_name}: {speaker} just threw {move} into the middle of this fight and {opponent or 'the other side'} has to answer it now.",
        f"{speaker_name}: Ply {ply} just got loud. {speaker} played {move} and the board smells like {tag_text}.",
        f"{speaker_name}: {speaker} lands {move} and the arena immediately starts acting like the next reply better be perfect.",
    )
    index = sum(ord(char) for char in f"{speaker}:{move}:{ply}:{tag_text}") % len(
        choices
    )
    return {
        "role": "showmatch",
        "speaker": speaker_name,
        "category": "hype",
        "target": "crowd",
        "message": choices[index],
        "color": color,
        "player": speaker,
        "opponent": opponent,
        "move": move,
        "ply": ply,
        "tags": list(tags),
    }


def build_showmatch_finish(
    *,
    speaker_name: str,
    result: str | None,
    termination_reason: str | None,
    winner: str | None,
    loser: str | None,
) -> dict[str, Any]:
    reason = termination_reason or "game_over"
    if result == "1/2-1/2":
        message = (
            f"{speaker_name}: All that heat and nobody found daylight. "
            "This one goes in the books as a draw."
        )
    elif (
        termination_reason and "checkmate" in termination_reason and winner is not None
    ):
        message = (
            f"{speaker_name}: {winner} just slammed the cage door shut on {loser or 'the other side'}. "
            "That is a full-arena checkmate finish."
        )
    elif winner is not None:
        message = f"{speaker_name}: {winner} takes the show and leaves {loser or 'the other side'} to explain the smoke."
    else:
        message = f"{speaker_name}: The show is over. Official ending: {reason}."
    return {
        "role": "showmatch",
        "speaker": speaker_name,
        "category": "finish",
        "target": "crowd",
        "message": message,
        "result": result,
        "termination_reason": reason,
        "winner": winner,
        "loser": loser,
    }


def build_showmatch_illegal_move_callout(
    *,
    speaker_name: str,
    color: str,
    speaker: str,
    move_text: str | None,
    reason: str,
    detail: str,
) -> dict[str, Any]:
    attempted = f" trying {move_text!r}" if move_text else ""
    return {
        "role": "showmatch",
        "speaker": speaker_name,
        "category": "illegal_move_callout",
        "target": "crowd",
        "message": (
            f"{speaker_name}: {speaker} just got the siren for {color}{attempted}. "
            f"Official reason: {reason}. {detail}"
        ),
        "color": color,
        "player": speaker,
        "move_text": move_text,
        "reason": reason,
        "detail": detail,
    }


def build_showmatch_postgame_interview(
    *,
    interviewer_name: str,
    player: str,
    stance: str,
    result: str | None,
    termination_reason: str | None,
) -> dict[str, Any]:
    if stance == "winner":
        message = (
            f"{player}: That board got loud and I stayed louder. "
            "Tell the next opponent to bring better excuses."
        )
    elif stance == "loser":
        message = f"{player}: I had ideas, the board had consequences, and now we all have tape."
    else:
        message = (
            f"{player}: Nobody got the knockout, but nobody got peace either. "
            "Run it back."
        )
    return {
        "role": "showmatch",
        "speaker": player,
        "category": "postgame_interview",
        "target": "crowd",
        "message": message,
        "interviewer": interviewer_name,
        "stance": stance,
        "result": result,
        "termination_reason": termination_reason or "game_over",
    }


def build_showmatch_rivalry_recap(
    *,
    speaker_name: str,
    white_player: str,
    black_player: str,
    result: str | None,
    banter_count: int,
    illegal_move_count: int,
) -> dict[str, Any]:
    return {
        "role": "showmatch",
        "speaker": speaker_name,
        "category": "rivalry_recap",
        "target": "crowd",
        "message": (
            f"{speaker_name}: {white_player} and {black_player} just gave us "
            f"{banter_count} notable mouthy moments, {illegal_move_count} rules-engine interventions, "
            f"and a final result of {result or '*'}. This rivalry has excellent bad manners."
        ),
        "white_player": white_player,
        "black_player": black_player,
        "result": result,
        "banter_count": banter_count,
        "illegal_move_count": illegal_move_count,
    }


def build_showmatch_quote_pin(
    *,
    speaker_name: str,
    quoted_speaker: str,
    quoted_message: str,
    rank: int,
    source_category: str,
) -> dict[str, Any]:
    return {
        "role": "showmatch",
        "speaker": speaker_name,
        "category": "quote_pin",
        "target": "crowd",
        "message": f'Quote #{rank}: "{quoted_message}" - {quoted_speaker}',
        "quoted_speaker": quoted_speaker,
        "quoted_message": quoted_message,
        "rank": rank,
        "source_category": source_category,
    }
