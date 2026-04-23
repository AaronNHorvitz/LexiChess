from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from lexichess.index.models import RatingSnapshot


class EloMatchResult(float, Enum):
    WIN = 1.0
    DRAW = 0.5
    LOSS = 0.0


@dataclass(frozen=True, slots=True)
class EloUpdate:
    player: RatingSnapshot
    opponent: RatingSnapshot
    expected_score: float
    actual_score: float
    new_rating: float
    new_games_played: int
    provisional: bool


def expected_score(player_rating: float, opponent_rating: float) -> float:
    return 1.0 / (1.0 + 10 ** ((opponent_rating - player_rating) / 400.0))


def apply_elo_result(
    player: RatingSnapshot,
    opponent: RatingSnapshot,
    result: EloMatchResult,
    *,
    k_factor: float = 32.0,
    provisional_threshold: int = 20,
) -> EloUpdate:
    expected = expected_score(player.rating, opponent.rating)
    new_rating = player.rating + k_factor * (float(result) - expected)
    new_games_played = player.games_played + 1
    return EloUpdate(
        player=player,
        opponent=opponent,
        expected_score=expected,
        actual_score=float(result),
        new_rating=new_rating,
        new_games_played=new_games_played,
        provisional=new_games_played < provisional_threshold,
    )
