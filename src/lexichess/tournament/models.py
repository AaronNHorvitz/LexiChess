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
