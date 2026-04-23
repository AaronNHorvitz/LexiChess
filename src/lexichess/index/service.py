from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from lexichess.index.anchors import default_engine_anchors
from lexichess.index.models import CompetitorIdentity, RatingSnapshot
from lexichess.index.ratings import EloMatchResult, apply_elo_result
from lexichess.storage import SQLiteRepository


@dataclass(frozen=True, slots=True)
class MatchRatingUpdate:
    white_before: RatingSnapshot
    black_before: RatingSnapshot
    white_after: RatingSnapshot
    black_after: RatingSnapshot
    result: str
    source_game_id: int | None = None


def identity_from_game(
    game: Mapping[str, Any],
    turns: Sequence[Mapping[str, Any]],
    *,
    color: str,
    runtime: str | None = None,
    prompt_profile: str | None = None,
    quantization: str | None = None,
    hardware_class: str | None = None,
    revision: str | None = None,
) -> CompetitorIdentity:
    if color not in {"white", "black"}:
        raise ValueError(f"Unsupported color: {color}")

    provider = str(game[f"{color}_provider"])
    model = str(game[f"{color}_model"])
    inferred_runtime = runtime or provider
    inferred_prompt = prompt_profile or _infer_prompt_profile(turns, color=color)
    return CompetitorIdentity(
        provider=provider,
        model=model,
        runtime=inferred_runtime,
        prompt_profile=inferred_prompt,
        quantization=quantization,
        hardware_class=hardware_class,
        revision=revision,
    )


def latest_or_default_snapshot(
    repository: SQLiteRepository,
    competitor: CompetitorIdentity,
) -> RatingSnapshot:
    row = repository.latest_rating_snapshot(competitor.slug)
    if row is not None:
        return RatingSnapshot(
            competitor=competitor,
            rating=float(row["rating"]),
            games_played=int(row["games_played"]),
            provisional=bool(row["provisional"]),
        )

    anchor = _anchor_for_identity(competitor)
    if anchor is not None:
        return RatingSnapshot(
            competitor=competitor,
            rating=anchor.starting_rating,
            games_played=0,
            provisional=True,
        )

    return RatingSnapshot(competitor=competitor)


def rate_completed_game(
    repository: SQLiteRepository,
    *,
    white: CompetitorIdentity,
    black: CompetitorIdentity,
    result: str,
    source_game_id: int | None = None,
) -> MatchRatingUpdate:
    white_before = latest_or_default_snapshot(repository, white)
    black_before = latest_or_default_snapshot(repository, black)

    white_result, black_result = _match_results_for_outcome(result)
    white_update = apply_elo_result(white_before, black_before, white_result)
    black_update = apply_elo_result(black_before, white_before, black_result)

    white_after = RatingSnapshot(
        competitor=white,
        rating=white_update.new_rating,
        games_played=white_update.new_games_played,
        provisional=white_update.provisional,
    )
    black_after = RatingSnapshot(
        competitor=black,
        rating=black_update.new_rating,
        games_played=black_update.new_games_played,
        provisional=black_update.provisional,
    )

    repository.record_rating_snapshot(
        white_after,
        source_game_id=source_game_id,
        source_result=result,
    )
    repository.record_rating_snapshot(
        black_after,
        source_game_id=source_game_id,
        source_result=result,
    )

    return MatchRatingUpdate(
        white_before=white_before,
        black_before=black_before,
        white_after=white_after,
        black_after=black_after,
        result=result,
        source_game_id=source_game_id,
    )


def rate_recorded_game(
    repository: SQLiteRepository,
    game_id: int,
    *,
    white_runtime: str | None = None,
    black_runtime: str | None = None,
    white_prompt_profile: str | None = None,
    black_prompt_profile: str | None = None,
    white_quantization: str | None = None,
    black_quantization: str | None = None,
    white_hardware_class: str | None = None,
    black_hardware_class: str | None = None,
    white_revision: str | None = None,
    black_revision: str | None = None,
) -> MatchRatingUpdate:
    game = repository.get_game(game_id)
    if game is None:
        raise ValueError(f"Game {game_id} was not found.")

    result = game.get("result")
    if not isinstance(result, str) or result not in {"1-0", "0-1", "1/2-1/2"}:
        raise ValueError(
            f"Game {game_id} does not have a rateable result. "
            "Expected one of 1-0, 0-1, or 1/2-1/2."
        )

    turns = repository.list_turns(game_id)
    white_identity = identity_from_game(
        game,
        turns,
        color="white",
        runtime=white_runtime,
        prompt_profile=white_prompt_profile,
        quantization=white_quantization,
        hardware_class=white_hardware_class,
        revision=white_revision,
    )
    black_identity = identity_from_game(
        game,
        turns,
        color="black",
        runtime=black_runtime,
        prompt_profile=black_prompt_profile,
        quantization=black_quantization,
        hardware_class=black_hardware_class,
        revision=black_revision,
    )
    return rate_completed_game(
        repository,
        white=white_identity,
        black=black_identity,
        result=result,
        source_game_id=game_id,
    )


def _infer_prompt_profile(
    turns: Sequence[Mapping[str, Any]],
    *,
    color: str,
) -> str:
    for turn in turns:
        if turn.get("color") == color:
            prompt_version = turn.get("prompt_version")
            if isinstance(prompt_version, str) and prompt_version:
                return prompt_version
            prompt_kind = turn.get("prompt_kind")
            if isinstance(prompt_kind, str) and prompt_kind:
                return prompt_kind
    return "benchmark_move.v2"


def _match_results_for_outcome(result: str) -> tuple[EloMatchResult, EloMatchResult]:
    if result == "1-0":
        return EloMatchResult.WIN, EloMatchResult.LOSS
    if result == "0-1":
        return EloMatchResult.LOSS, EloMatchResult.WIN
    if result == "1/2-1/2":
        return EloMatchResult.DRAW, EloMatchResult.DRAW
    raise ValueError(f"Unsupported game result for rating: {result}")


def _anchor_for_identity(
    competitor: CompetitorIdentity,
) -> Any | None:
    for anchor in default_engine_anchors():
        if anchor.identity.slug == competitor.slug:
            return anchor
    return None
