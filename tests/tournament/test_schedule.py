from __future__ import annotations

from lexichess.tournament.models import PlayerSpec
from lexichess.tournament.schedule import (
    build_anchor_benchmark_schedule,
    build_round_robin_schedule,
)


def test_round_robin_schedule_generates_home_and_away_pairings() -> None:
    players = [
        PlayerSpec("ollama", "qwen3:8b"),
        PlayerSpec("ollama", "deepseek-r1:14b"),
        PlayerSpec("stockfish", "stockfish_club"),
    ]

    schedule = build_round_robin_schedule(players)

    assert len(schedule) == 6
    assert schedule[0].white.model == "qwen3:8b"
    assert schedule[1].white.model == "deepseek-r1:14b"
    assert schedule[1].black.model == "qwen3:8b"


def test_anchor_benchmark_schedule_alternates_colors() -> None:
    challenger = PlayerSpec("ollama", "qwen3:8b")

    schedule = build_anchor_benchmark_schedule(
        challenger,
        anchor_names=["stockfish_beginner", "stockfish_club"],
        games_per_anchor=2,
    )

    assert len(schedule) == 4
    assert schedule[0].white.model == "qwen3:8b"
    assert schedule[0].black.model == "stockfish_beginner"
    assert schedule[1].white.model == "stockfish_beginner"
    assert schedule[1].black.model == "qwen3:8b"
    assert schedule[2].black.model == "stockfish_club"
