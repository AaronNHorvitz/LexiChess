from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

from lexichess.index.anchors import default_engine_anchors, get_engine_anchor
from lexichess.tournament.models import PlayerSpec


@dataclass(frozen=True, slots=True)
class ScheduledMatch:
    match_number: int
    round_number: int
    white: PlayerSpec
    black: PlayerSpec
    tag: str | None = None


def build_round_robin_schedule(
    players: Sequence[PlayerSpec],
    *,
    double_round_robin: bool = True,
) -> list[ScheduledMatch]:
    schedule: list[ScheduledMatch] = []
    match_number = 1
    round_number = 1
    for white, black in combinations(players, 2):
        schedule.append(
            ScheduledMatch(
                match_number=match_number,
                round_number=round_number,
                white=white,
                black=black,
                tag="round_robin",
            )
        )
        match_number += 1
        round_number += 1
        if double_round_robin:
            schedule.append(
                ScheduledMatch(
                    match_number=match_number,
                    round_number=round_number,
                    white=black,
                    black=white,
                    tag="round_robin_return",
                )
            )
            match_number += 1
            round_number += 1
    return schedule


def build_anchor_benchmark_schedule(
    challenger: PlayerSpec,
    *,
    anchor_names: Sequence[str] | None = None,
    games_per_anchor: int = 2,
) -> list[ScheduledMatch]:
    if games_per_anchor < 1:
        raise ValueError("games_per_anchor must be at least 1.")

    resolved_anchor_names = (
        list(anchor_names)
        if anchor_names
        else [anchor.name for anchor in default_engine_anchors()]
    )
    anchor_players = [_anchor_player_spec(name) for name in resolved_anchor_names]

    schedule: list[ScheduledMatch] = []
    match_number = 1
    round_number = 1
    for anchor in anchor_players:
        for game_index in range(games_per_anchor):
            challenger_is_white = game_index % 2 == 0
            white = challenger if challenger_is_white else anchor
            black = anchor if challenger_is_white else challenger
            schedule.append(
                ScheduledMatch(
                    match_number=match_number,
                    round_number=round_number,
                    white=white,
                    black=black,
                    tag=f"anchor:{anchor.label}",
                )
            )
            match_number += 1
            round_number += 1
    return schedule


def _anchor_player_spec(name: str) -> PlayerSpec:
    anchor = get_engine_anchor(name)
    if anchor is None:
        raise ValueError(f"Unknown engine anchor: {name}")
    return PlayerSpec(
        provider_name=anchor.identity.provider,
        model=anchor.identity.model,
        display_name=anchor.name,
    )
