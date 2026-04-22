from __future__ import annotations

import re
from dataclasses import dataclass

import chess

UCI_PATTERN = re.compile(r"\b[a-h][1-8][a-h][1-8][qrbn]?\b", re.IGNORECASE)
SAN_PATTERN = re.compile(
    r"\b(?:O-O-O|O-O|0-0-0|0-0|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?|[a-h][1-8](?:=[QRBN])?[+#]?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class MoveInterpretation:
    raw_text: str
    candidate: str | None
    san: str | None
    uci: str | None
    reason: str | None = None


def interpret_move_text(board: chess.Board, text: str) -> MoveInterpretation:
    stripped = text.strip()
    if not stripped:
        return MoveInterpretation(
            raw_text=text,
            candidate=None,
            san=None,
            uci=None,
            reason="empty_response",
        )

    first_candidate: str | None = None
    saw_move_like_candidate = False

    for candidate in extract_move_candidates(stripped):
        cleaned = _clean_candidate(candidate)
        if not cleaned:
            continue

        if first_candidate is None:
            first_candidate = cleaned

        move = _parse_san_candidate(board, cleaned)
        if move is not None:
            return MoveInterpretation(
                raw_text=text,
                candidate=cleaned,
                san=board.san(move),
                uci=move.uci(),
            )

        move = _parse_uci_candidate(board, cleaned)
        if move is not None:
            return MoveInterpretation(
                raw_text=text,
                candidate=cleaned,
                san=board.san(move),
                uci=move.uci(),
            )

        if _looks_like_move(cleaned):
            saw_move_like_candidate = True

    return MoveInterpretation(
        raw_text=text,
        candidate=first_candidate,
        san=None,
        uci=None,
        reason=(
            "invalid_or_illegal_move"
            if saw_move_like_candidate
            else "no_candidate_found"
        ),
    )


def extract_move_candidates(text: str) -> list[str]:
    candidates: list[str] = []

    _append_candidate(candidates, text)

    for line in text.splitlines():
        _append_candidate(candidates, line.strip())

    for match in re.findall(r"`([^`]+)`", text):
        _append_candidate(candidates, match)

    for match in UCI_PATTERN.finditer(text):
        _append_candidate(candidates, match.group(0))

    for match in SAN_PATTERN.finditer(text):
        _append_candidate(candidates, match.group(0))

    return _dedupe(candidates)


def _append_candidate(candidates: list[str], candidate: str) -> None:
    if candidate:
        candidates.append(candidate)


def _dedupe(candidates: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped


def _clean_candidate(candidate: str) -> str:
    cleaned = candidate.strip().strip("`'\"")
    cleaned = cleaned.strip("[]{}()<>")
    cleaned = cleaned.rstrip(".,;:!?")
    cleaned = cleaned.replace("0-0-0", "O-O-O").replace("0-0", "O-O")
    if cleaned.lower() == "o-o-o":
        return "O-O-O"
    if cleaned.lower() == "o-o":
        return "O-O"
    if cleaned.lower().startswith("move:"):
        return cleaned.split(":", 1)[1].strip()
    return cleaned


def _looks_like_move(candidate: str) -> bool:
    return bool(
        UCI_PATTERN.fullmatch(candidate.replace("-", ""))
        or SAN_PATTERN.fullmatch(candidate)
    )


def _parse_san_candidate(board: chess.Board, candidate: str) -> chess.Move | None:
    try:
        return board.parse_san(candidate)
    except ValueError:
        return None


def _parse_uci_candidate(board: chess.Board, candidate: str) -> chess.Move | None:
    normalized = candidate.replace("-", "").lower()
    if not UCI_PATTERN.fullmatch(normalized):
        return None

    try:
        move = chess.Move.from_uci(normalized)
    except ValueError:
        return None

    if move in board.legal_moves:
        return move
    return None
