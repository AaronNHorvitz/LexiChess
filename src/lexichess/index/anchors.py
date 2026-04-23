from __future__ import annotations

from lexichess.index.models import AnchorCompetitor, CompetitorIdentity


def default_engine_anchors() -> list[AnchorCompetitor]:
    anchors = [
        ("stockfish_beginner", 1000.0, "Very limited Stockfish baseline."),
        ("stockfish_club", 1400.0, "Club-strength Stockfish baseline."),
        ("stockfish_tournament", 1800.0, "Tournament-strength Stockfish baseline."),
        ("stockfish_expert", 2200.0, "Expert-strength Stockfish baseline."),
        ("stockfish_master", 2600.0, "Master-strength Stockfish baseline."),
    ]
    return [
        AnchorCompetitor(
            name=name,
            identity=CompetitorIdentity(
                provider="engine",
                model=name,
                runtime="stockfish",
                prompt_profile="engine_anchor",
            ),
            starting_rating=rating,
            description=description,
        )
        for name, rating, description in anchors
    ]
