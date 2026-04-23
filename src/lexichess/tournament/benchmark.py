from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from lexichess.analysis import StockfishEngine
from lexichess.config import AppSettings
from lexichess.index import MatchRatingUpdate, rate_recorded_game
from lexichess.llm.registry import build_provider
from lexichess.storage import SQLiteRepository
from lexichess.tournament.models import GameResult, PlayerSpec
from lexichess.tournament.runner import GameRunner
from lexichess.tournament.schedule import (
    ScheduledMatch,
    build_anchor_benchmark_schedule,
)


@dataclass(frozen=True, slots=True)
class ScheduledMatchResult:
    match: ScheduledMatch
    game: GameResult
    rating_update: MatchRatingUpdate | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkRunSummary:
    matches: tuple[ScheduledMatchResult, ...]


def run_anchor_benchmark(
    *,
    challenger: PlayerSpec,
    settings: AppSettings,
    repository: SQLiteRepository,
    anchor_names: Sequence[str] | None = None,
    games_per_anchor: int = 2,
    max_plies: int | None = None,
    max_correction_attempts: int = 1,
    record_engine_analysis: bool = True,
    auto_rate: bool = True,
) -> BenchmarkRunSummary:
    schedule = build_anchor_benchmark_schedule(
        challenger,
        anchor_names=anchor_names,
        games_per_anchor=games_per_anchor,
    )
    analysis_engine = (
        StockfishEngine(
            path=settings.stockfish.path,
            depth=settings.stockfish.depth,
            multipv=settings.stockfish.multipv,
            movetime_ms=settings.stockfish.movetime_ms,
        )
        if record_engine_analysis
        else None
    )
    return run_schedule(
        schedule,
        settings=settings,
        repository=repository,
        max_plies=max_plies,
        max_correction_attempts=max_correction_attempts,
        analysis_engine=analysis_engine,
        auto_rate=auto_rate,
    )


def run_schedule(
    schedule: Sequence[ScheduledMatch],
    *,
    settings: AppSettings,
    repository: SQLiteRepository,
    max_plies: int | None = None,
    max_correction_attempts: int = 1,
    analysis_engine: StockfishEngine | None = None,
    auto_rate: bool = True,
) -> BenchmarkRunSummary:
    repository.initialize()

    results: list[ScheduledMatchResult] = []
    for match in schedule:
        white_provider = build_provider(
            match.white.provider_name,
            settings,
            model=match.white.model,
        )
        black_provider = build_provider(
            match.black.provider_name,
            settings,
            model=match.black.model,
        )
        runner = GameRunner(
            white_provider=white_provider,
            black_provider=black_provider,
            repository=repository,
            max_plies=max_plies or settings.max_plies,
            move_temperature=settings.move_temperature,
            max_output_tokens=settings.max_output_tokens,
            log_raw_response_json=settings.log_raw_response_json,
            max_correction_attempts=max_correction_attempts,
            analysis_engine=analysis_engine,
        )
        game = runner.play()
        rating_update = None
        if auto_rate and game.result in {"1-0", "0-1", "1/2-1/2"}:
            rating_update = rate_recorded_game(repository, game.game_id)
        results.append(
            ScheduledMatchResult(
                match=match,
                game=game,
                rating_update=rating_update,
            )
        )

    return BenchmarkRunSummary(matches=tuple(results))
