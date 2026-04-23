from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompetitorIdentity:
    provider: str
    model: str
    runtime: str
    prompt_profile: str
    quantization: str | None = None
    hardware_class: str | None = None
    revision: str | None = None

    @property
    def slug(self) -> str:
        parts = [
            self.provider,
            self.model,
            self.runtime,
            self.prompt_profile,
            self.quantization,
            self.hardware_class,
            self.revision,
        ]
        return ":".join(part for part in parts if part)


@dataclass(frozen=True, slots=True)
class RatingSnapshot:
    competitor: CompetitorIdentity
    rating: float = 1500.0
    games_played: int = 0
    provisional: bool = True


@dataclass(frozen=True, slots=True)
class AnchorCompetitor:
    name: str
    identity: CompetitorIdentity
    starting_rating: float
    description: str
