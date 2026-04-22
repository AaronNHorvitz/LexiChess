from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class MoveRequest:
    game_id: int | None
    move_number: int
    color: str
    fen: str
    prompt: str
    instructions: str
    legal_moves: tuple[str, ...]
    temperature: float | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    provider: str
    model: str
    output_text: str
    raw_response: dict[str, Any] | None = None
    latency_ms: int | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    finish_reason: str | None = None
