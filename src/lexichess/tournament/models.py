from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlayerSpec:
    provider_name: str
    model: str
    display_name: str | None = None

    @property
    def label(self) -> str:
        return self.display_name or f"{self.provider_name}:{self.model}"


@dataclass(frozen=True, slots=True)
class GameResult:
    game_id: int
    status: str
    result: str | None
    termination_reason: str | None
    moves: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InvalidMoveNotification:
    game_id: int
    ply: int
    attempt: int
    color: str
    provider: str
    model: str
    fen: str
    raw_response_text: str
    candidate_move: str | None
    reason: str
    deterministic_explanation: str
    legal_moves: tuple[str, ...]
    prompt_kind: str
    prompt_version: str
