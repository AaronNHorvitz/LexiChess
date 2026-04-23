from __future__ import annotations

from dataclasses import dataclass

from lexichess.chess import ChessBoard
from lexichess.tournament.models import InvalidMoveNotification

BENCHMARK_MOVE_PROMPT_VERSION = "benchmark_move.v2"
INVALID_MOVE_RETRY_PROMPT_VERSION = "invalid_move_retry.v1"
REFEREE_COACHING_PROMPT_VERSION = "referee_coaching.v1"

STRUCTURED_MOVE_INSTRUCTIONS = (
    "You are playing chess. Reply with exactly one line in the form "
    "'MOVE: <SAN>'. Do not include commentary, analysis, or multiple moves."
)


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    kind: str
    version: str
    instructions: str
    prompt: str


def build_benchmark_move_prompt(
    board: ChessBoard, legal_moves: tuple[str, ...]
) -> PromptTemplate:
    move_history = " ".join(board.move_history_san()) or "None"
    legal_move_list = ", ".join(legal_moves)
    return PromptTemplate(
        kind="benchmark_move",
        version=BENCHMARK_MOVE_PROMPT_VERSION,
        instructions=STRUCTURED_MOVE_INSTRUCTIONS,
        prompt=(
            f"You are playing as {board.turn_color}.\n"
            f"Current FEN: {board.fen}\n"
            f"Moves played so far (SAN): {move_history}\n"
            f"Legal moves available (SAN): {legal_move_list}\n"
            "Output format:\n"
            "MOVE: <SAN>"
        ),
    )


def build_invalid_move_retry_prompt(
    board: ChessBoard,
    legal_moves: tuple[str, ...],
    notification: InvalidMoveNotification,
    *,
    referee_note: str | None = None,
) -> PromptTemplate:
    legal_move_list = ", ".join(legal_moves)
    referee_block = (
        f"Referee guidance:\n{referee_note}\n" if referee_note is not None else ""
    )
    return PromptTemplate(
        kind="invalid_move_retry",
        version=INVALID_MOVE_RETRY_PROMPT_VERSION,
        instructions=STRUCTURED_MOVE_INSTRUCTIONS,
        prompt=(
            f"You are replaying ply {notification.ply} as {board.turn_color}.\n"
            f"Current FEN: {board.fen}\n"
            f"Your previous reply was rejected: {notification.raw_response_text!r}\n"
            f"Deterministic rejection reason: {notification.deterministic_explanation}\n"
            f"{referee_block}"
            f"Legal moves available (SAN): {legal_move_list}\n"
            "Choose exactly one legal replacement move.\n"
            "Output format:\n"
            "MOVE: <SAN>"
        ),
    )


def build_referee_coaching_prompt(
    notification: InvalidMoveNotification,
) -> PromptTemplate:
    return PromptTemplate(
        kind="referee_coaching",
        version=REFEREE_COACHING_PROMPT_VERSION,
        instructions=(
            "You are the rational chess referee. Reply with one or two sentences that "
            "briefly explain the rule issue and coach the player toward submitting a "
            "legal SAN move. Do not choose a move for them."
        ),
        prompt=(
            f"Color to move: {notification.color}\n"
            f"FEN: {notification.fen}\n"
            f"Rejected reply: {notification.raw_response_text!r}\n"
            f"Candidate move: {notification.candidate_move!r}\n"
            f"Deterministic explanation: {notification.deterministic_explanation}\n"
            f"Legal moves: {', '.join(notification.legal_moves)}"
        ),
    )
