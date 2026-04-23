from __future__ import annotations

from pathlib import Path

from lexichess.index.models import CompetitorIdentity, RatingSnapshot
from lexichess.index.reporting import (
    build_chess_index_snapshot,
    render_chess_index_markdown,
)
from lexichess.storage import SQLiteRepository


def test_chess_index_snapshot_aggregates_latest_ratings(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "chess_index_reporting.db")
    repository.initialize()

    competitor_one = CompetitorIdentity(
        provider="stockfish",
        model="stockfish_club",
        runtime="stockfish",
        prompt_profile="engine_anchor",
    )
    competitor_two = CompetitorIdentity(
        provider="ollama",
        model="qwen3:8b",
        runtime="ollama",
        prompt_profile="benchmark_move.v2",
    )
    repository.record_rating_snapshot(
        RatingSnapshot(competitor=competitor_one, rating=1400.0, games_played=1),
        source_result="1-0",
        competitor_result="win",
    )
    repository.record_rating_snapshot(
        RatingSnapshot(competitor=competitor_one, rating=1415.0, games_played=2),
        source_result="1/2-1/2",
        competitor_result="draw",
    )
    repository.record_rating_snapshot(
        RatingSnapshot(competitor=competitor_two, rating=1505.0, games_played=1),
        source_result="0-1",
        competitor_result="loss",
    )

    snapshot = build_chess_index_snapshot(
        repository,
        limit=10,
        include_provisional=True,
    )

    assert snapshot.included_competitors == 2
    assert snapshot.entries[0].competitor_slug == competitor_two.slug
    assert snapshot.entries[1].wins == 1
    assert snapshot.entries[1].draws == 1
    assert snapshot.entries[1].losses == 0
    assert snapshot.entries[0].last_result == "loss"

    markdown = render_chess_index_markdown(snapshot)
    assert "# LexiChess Chess Index" in markdown
    assert competitor_one.slug in markdown
