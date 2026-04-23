from __future__ import annotations

from lexichess.index import (
    CompetitorIdentity,
    EloMatchResult,
    RatingSnapshot,
    apply_elo_result,
    default_engine_anchors,
    expected_score,
)


def test_competitor_identity_slug_and_anchor_defaults() -> None:
    identity = CompetitorIdentity(
        provider="ollama",
        model="qwen3:8b",
        runtime="ollama",
        prompt_profile="benchmark_move.v2",
        quantization="q4_k_m",
        hardware_class="4090",
    )

    anchors = default_engine_anchors()

    assert "ollama:qwen3:8b:ollama:benchmark_move.v2:q4_k_m:4090" == identity.slug
    assert len(anchors) >= 5
    assert anchors[0].starting_rating < anchors[-1].starting_rating


def test_elo_update_increases_rating_after_win() -> None:
    player = RatingSnapshot(
        competitor=CompetitorIdentity(
            provider="ollama",
            model="qwen3:8b",
            runtime="ollama",
            prompt_profile="benchmark_move.v2",
        ),
        rating=1500.0,
        games_played=4,
        provisional=True,
    )
    opponent = RatingSnapshot(
        competitor=CompetitorIdentity(
            provider="engine",
            model="stockfish_club",
            runtime="stockfish",
            prompt_profile="engine_anchor",
        ),
        rating=1600.0,
        games_played=50,
        provisional=False,
    )

    expected = expected_score(player.rating, opponent.rating)
    update = apply_elo_result(player, opponent, EloMatchResult.WIN)

    assert expected < 0.5
    assert update.new_rating > player.rating
    assert update.new_games_played == 5
