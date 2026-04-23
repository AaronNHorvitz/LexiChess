from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

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
    build_round_robin_schedule,
)


@dataclass(frozen=True, slots=True)
class TournamentRunItem:
    pairing_id: int
    match_number: int
    round_number: int
    white_label: str
    black_label: str
    status: str
    game: GameResult | None = None
    rating_update: MatchRatingUpdate | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class TournamentRunSummary:
    tournament_id: int
    status: str
    processed: tuple[TournamentRunItem, ...]
    pending_pairings: int
    failed_pairings: int
    completed_pairings: int
    standings: tuple[dict[str, Any], ...]


def create_round_robin_tournament(
    repository: SQLiteRepository,
    *,
    name: str,
    players: Sequence[PlayerSpec],
    double_round_robin: bool = True,
    notes: str | None = None,
) -> int:
    if len(players) < 2:
        raise ValueError("Round-robin tournaments require at least two players.")

    schedule = build_round_robin_schedule(
        players,
        double_round_robin=double_round_robin,
    )
    return _create_tournament_from_schedule(
        repository,
        name=name,
        tournament_format="round_robin",
        players=players,
        schedule=schedule,
        notes=notes,
        config={
            "double_round_robin": double_round_robin,
            "scheduled_pairings": len(schedule),
            "player_count": len(players),
        },
    )


def create_anchor_tournament(
    repository: SQLiteRepository,
    *,
    name: str,
    challenger: PlayerSpec,
    anchor_names: Sequence[str] | None = None,
    games_per_anchor: int = 2,
    notes: str | None = None,
) -> int:
    schedule = build_anchor_benchmark_schedule(
        challenger,
        anchor_names=anchor_names,
        games_per_anchor=games_per_anchor,
    )
    players: list[PlayerSpec] = []
    seen: set[PlayerSpec] = set()
    for match in schedule:
        for player in (match.white, match.black):
            if player not in seen:
                players.append(player)
                seen.add(player)
    return _create_tournament_from_schedule(
        repository,
        name=name,
        tournament_format="anchor_benchmark",
        players=players,
        schedule=schedule,
        notes=notes,
        config={
            "anchor_names": list(anchor_names) if anchor_names is not None else None,
            "games_per_anchor": games_per_anchor,
            "scheduled_pairings": len(schedule),
            "player_count": len(players),
        },
    )


def run_tournament(
    repository: SQLiteRepository,
    *,
    tournament_id: int,
    settings: AppSettings,
    max_matches: int | None = None,
    max_plies: int | None = None,
    max_correction_attempts: int = 1,
    record_engine_analysis: bool = True,
    auto_rate: bool = True,
    include_failed: bool = False,
) -> TournamentRunSummary:
    tournament = repository.get_tournament(tournament_id)
    if tournament is None:
        raise ValueError(f"Tournament {tournament_id} was not found.")
    if tournament["status"] == "completed":
        return _summary_for_current_state(repository, tournament_id=tournament_id)

    selected_statuses = ("pending", "failed") if include_failed else ("pending",)
    pairings = repository.list_tournament_pairings(
        tournament_id,
        statuses=selected_statuses,
    )
    if max_matches is not None:
        pairings = pairings[:max_matches]

    repository.update_tournament_status(tournament_id, status="running")
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

    processed: list[TournamentRunItem] = []
    for pairing in pairings:
        pairing_id = int(pairing["id"])
        repository.start_tournament_pairing(pairing_id)
        try:
            white_provider = build_provider(
                str(pairing["white_provider"]),
                settings,
                model=str(pairing["white_model"]),
            )
            black_provider = build_provider(
                str(pairing["black_provider"]),
                settings,
                model=str(pairing["black_model"]),
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
        except Exception as exc:
            message = str(exc)
            repository.pause_tournament_pairing(
                pairing_id,
                error_message=message,
            )
            repository.update_tournament_status(tournament_id, status="paused")
            processed.append(
                TournamentRunItem(
                    pairing_id=pairing_id,
                    match_number=int(pairing["match_number"]),
                    round_number=int(pairing["round_number"]),
                    white_label=str(pairing["white_label"]),
                    black_label=str(pairing["black_label"]),
                    status="failed",
                    error_message=message,
                )
            )
            return _summary_for_current_state(
                repository,
                tournament_id=tournament_id,
                processed=processed,
            )

        repository.finish_tournament_pairing(
            pairing_id,
            status="completed",
            game_id=game.game_id,
            result=game.result,
            termination_reason=game.termination_reason,
        )

        rating_update = None
        if auto_rate and game.result in {"1-0", "0-1", "1/2-1/2"}:
            rating_update = rate_recorded_game(repository, game.game_id)

        processed.append(
            TournamentRunItem(
                pairing_id=pairing_id,
                match_number=int(pairing["match_number"]),
                round_number=int(pairing["round_number"]),
                white_label=str(pairing["white_label"]),
                black_label=str(pairing["black_label"]),
                status="completed",
                game=game,
                rating_update=rating_update,
            )
        )

    pending_pairings = repository.list_tournament_pairings(
        tournament_id,
        statuses=("pending",),
    )
    failed_pairings = repository.list_tournament_pairings(
        tournament_id,
        statuses=("failed",),
    )
    if not pending_pairings and not failed_pairings:
        repository.update_tournament_status(tournament_id, status="completed")
    elif processed:
        repository.update_tournament_status(tournament_id, status="paused")

    return _summary_for_current_state(
        repository,
        tournament_id=tournament_id,
        processed=processed,
    )


def pause_tournament(repository: SQLiteRepository, tournament_id: int) -> None:
    tournament = repository.get_tournament(tournament_id)
    if tournament is None:
        raise ValueError(f"Tournament {tournament_id} was not found.")
    if tournament["status"] == "completed":
        return
    repository.update_tournament_status(tournament_id, status="paused")


def _create_tournament_from_schedule(
    repository: SQLiteRepository,
    *,
    name: str,
    tournament_format: str,
    players: Sequence[PlayerSpec],
    schedule: Sequence[ScheduledMatch],
    config: dict[str, Any],
    notes: str | None = None,
) -> int:
    repository.initialize()
    tournament_id = repository.create_tournament(
        name=name,
        tournament_format=tournament_format,
        config=config,
        notes=notes,
    )
    player_ids: dict[PlayerSpec, int] = {}
    for seed, player in enumerate(players, start=1):
        player_ids[player] = repository.add_tournament_player(
            tournament_id,
            provider=player.provider_name,
            model=player.model,
            display_name=player.display_name,
            seed=seed,
        )
    repository.create_tournament_pairings(
        tournament_id,
        [
            {
                "match_number": match.match_number,
                "round_number": match.round_number,
                "white_player_id": player_ids[match.white],
                "black_player_id": player_ids[match.black],
                "tag": match.tag,
            }
            for match in schedule
        ],
    )
    return tournament_id


def _summary_for_current_state(
    repository: SQLiteRepository,
    *,
    tournament_id: int,
    processed: Sequence[TournamentRunItem] | None = None,
) -> TournamentRunSummary:
    tournament = repository.get_tournament(tournament_id)
    if tournament is None:
        raise ValueError(f"Tournament {tournament_id} was not found.")
    pending = repository.list_tournament_pairings(tournament_id, statuses=("pending",))
    failed = repository.list_tournament_pairings(tournament_id, statuses=("failed",))
    completed = repository.list_tournament_pairings(
        tournament_id,
        statuses=("completed",),
    )
    standings = repository.compute_tournament_standings(tournament_id)
    return TournamentRunSummary(
        tournament_id=tournament_id,
        status=str(tournament["status"]),
        processed=tuple(processed or ()),
        pending_pairings=len(pending),
        failed_pairings=len(failed),
        completed_pairings=len(completed),
        standings=tuple(standings),
    )
