from __future__ import annotations

from lexichess.index.models import AnchorCompetitor, CompetitorIdentity


def default_engine_anchors() -> list[AnchorCompetitor]:
    anchors = [
        ("stockfish_beginner", 1000.0, "Very limited Stockfish baseline.", 4, 1),
        ("stockfish_club", 1400.0, "Club-strength Stockfish baseline.", 7, 1),
        (
            "stockfish_tournament",
            1800.0,
            "Tournament-strength Stockfish baseline.",
            10,
            1,
        ),
        ("stockfish_expert", 2200.0, "Expert-strength Stockfish baseline.", 13, 1),
        ("stockfish_master", 2600.0, "Master-strength Stockfish baseline.", 16, 1),
    ]
    return [
        AnchorCompetitor(
            name=name,
            identity=CompetitorIdentity(
                provider="stockfish",
                model=name,
                runtime="stockfish",
                prompt_profile="engine_anchor",
            ),
            starting_rating=rating,
            description=description,
            depth=depth,
            multipv=multipv,
        )
        for name, rating, description, depth, multipv in anchors
    ]


def get_engine_anchor(name: str) -> AnchorCompetitor | None:
    for anchor in default_engine_anchors():
        if anchor.name == name:
            return anchor
    return None
