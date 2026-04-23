from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from lexichess.analysis import StockfishEngine
from lexichess.config import AppSettings, ProviderName
from lexichess.index import (
    EloMatchResult,
    RatingSnapshot,
    apply_elo_result,
    build_chess_index_snapshot,
    default_engine_anchors,
    rate_recorded_game,
    render_chess_index_markdown,
)
from lexichess.llm.registry import build_provider
from lexichess.storage.repository import SQLiteRepository
from lexichess.tournament.replay import (
    build_game_bundle,
    export_game_json,
    render_move_list,
)
from lexichess.tournament import (
    PlayerSpec,
    create_anchor_tournament,
    create_round_robin_tournament,
    pause_tournament,
    run_anchor_benchmark,
    run_tournament,
)
from lexichess.tournament.export import (
    export_tournament_json,
    render_tournament_markdown,
)
from lexichess.tournament.runner import GameRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LexiChess MVP CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    settings_parser = subparsers.add_parser(
        "settings", help="Print the resolved application settings."
    )
    settings_parser.add_argument(
        "--json", action="store_true", help="Print the resolved settings as JSON."
    )

    play_parser = subparsers.add_parser(
        "play", help="Run a single game between two configured local model backends."
    )
    play_parser.add_argument(
        "--white-provider",
        choices=[provider.value for provider in ProviderName],
        help="Local runtime for the white player. Defaults to LEXICHESS_PROVIDER.",
    )
    play_parser.add_argument(
        "--white-model", help="Model override for the white player."
    )
    play_parser.add_argument(
        "--black-provider",
        choices=[provider.value for provider in ProviderName],
        help="Local runtime for the black player. Defaults to the white provider.",
    )
    play_parser.add_argument(
        "--black-model", help="Model override for the black player."
    )
    play_parser.add_argument("--fen", help="Optional starting FEN.")
    play_parser.add_argument(
        "--max-plies",
        type=int,
        help="Optional move cap override for the match runner.",
    )
    play_parser.add_argument(
        "--max-correction-attempts",
        type=int,
        default=1,
        help="Number of retry attempts after a deterministically rejected move.",
    )
    play_parser.add_argument("--db-path", help="Override the SQLite database path.")
    play_parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Disable post-move Stockfish analysis persistence for this game.",
    )
    play_parser.add_argument(
        "--quiet", action="store_true", help="Suppress the JSON game summary output."
    )

    list_parser = subparsers.add_parser(
        "list-games", help="List recently recorded games."
    )
    list_parser.add_argument("--db-path", help="Override the SQLite database path.")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--json", action="store_true")

    inspect_parser = subparsers.add_parser(
        "inspect-game", help="Inspect one recorded game, including turns and errors."
    )
    inspect_parser.add_argument("game_id", type=int)
    inspect_parser.add_argument("--db-path", help="Override the SQLite database path.")
    inspect_parser.add_argument("--json", action="store_true")

    replay_parser = subparsers.add_parser(
        "replay", help="Show the accepted move list for a recorded game."
    )
    replay_parser.add_argument("game_id", type=int)
    replay_parser.add_argument("--db-path", help="Override the SQLite database path.")
    replay_parser.add_argument("--json", action="store_true")

    export_parser = subparsers.add_parser(
        "export-game", help="Export a recorded game as JSON or PGN."
    )
    export_parser.add_argument("game_id", type=int)
    export_parser.add_argument("--db-path", help="Override the SQLite database path.")
    export_parser.add_argument("--format", choices=["json", "pgn"], default="json")
    export_parser.add_argument("--output", help="Write the export to a file.")

    diagnose_provider_parser = subparsers.add_parser(
        "diagnose-provider",
        help="Run provider health checks and list available models.",
    )
    diagnose_provider_parser.add_argument(
        "--provider",
        choices=[provider.value for provider in ProviderName],
        help="Provider to diagnose. Defaults to LEXICHESS_PROVIDER.",
    )
    diagnose_provider_parser.add_argument(
        "--model",
        help="Optional model override to test against the selected provider.",
    )
    diagnose_provider_parser.add_argument("--json", action="store_true")

    diagnose_stockfish_parser = subparsers.add_parser(
        "diagnose-stockfish",
        help="Run a Stockfish health check and optional position analysis.",
    )
    diagnose_stockfish_parser.add_argument(
        "--engine-path", help="Override engine path."
    )
    diagnose_stockfish_parser.add_argument("--fen", help="Optional FEN to analyze.")
    diagnose_stockfish_parser.add_argument("--depth", type=int)
    diagnose_stockfish_parser.add_argument("--multipv", type=int)
    diagnose_stockfish_parser.add_argument("--json", action="store_true")

    anchors_parser = subparsers.add_parser(
        "list-anchors", help="List the default engine anchor competitors."
    )
    anchors_parser.add_argument("--json", action="store_true")

    list_ratings_parser = subparsers.add_parser(
        "list-ratings", help="List the latest stored rating snapshots."
    )
    list_ratings_parser.add_argument(
        "--db-path", help="Override the SQLite database path."
    )
    list_ratings_parser.add_argument("--limit", type=int, default=50)
    list_ratings_parser.add_argument("--json", action="store_true")

    chess_index_parser = subparsers.add_parser(
        "chess-index",
        help="Build the current Chess Index leaderboard snapshot from stored ratings.",
    )
    chess_index_parser.add_argument("--db-path")
    chess_index_parser.add_argument("--limit", type=int, default=50)
    chess_index_parser.add_argument("--minimum-games", type=int, default=0)
    chess_index_parser.add_argument(
        "--include-provisional",
        action="store_true",
        help="Include provisional competitors in the leaderboard snapshot.",
    )
    chess_index_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    chess_index_parser.add_argument("--output")

    rating_history_parser = subparsers.add_parser(
        "rating-history", help="Show stored rating history for one competitor slug."
    )
    rating_history_parser.add_argument("competitor_slug")
    rating_history_parser.add_argument(
        "--db-path", help="Override the SQLite database path."
    )
    rating_history_parser.add_argument("--json", action="store_true")

    rate_game_parser = subparsers.add_parser(
        "rate-game", help="Record Elo snapshots for a completed game."
    )
    rate_game_parser.add_argument("game_id", type=int)
    rate_game_parser.add_argument(
        "--db-path", help="Override the SQLite database path."
    )
    rate_game_parser.add_argument("--white-runtime")
    rate_game_parser.add_argument("--black-runtime")
    rate_game_parser.add_argument("--white-prompt-profile")
    rate_game_parser.add_argument("--black-prompt-profile")
    rate_game_parser.add_argument("--white-quantization")
    rate_game_parser.add_argument("--black-quantization")
    rate_game_parser.add_argument("--white-hardware-class")
    rate_game_parser.add_argument("--black-hardware-class")
    rate_game_parser.add_argument("--white-revision")
    rate_game_parser.add_argument("--black-revision")
    rate_game_parser.add_argument("--json", action="store_true")

    anchor_benchmark_parser = subparsers.add_parser(
        "run-anchor-benchmark",
        help="Run and rate a batch of challenger-vs-anchor games.",
    )
    anchor_benchmark_parser.add_argument(
        "--challenger-provider",
        choices=[provider.value for provider in ProviderName],
        help="Provider for the challenger. Defaults to LEXICHESS_PROVIDER.",
    )
    anchor_benchmark_parser.add_argument(
        "--challenger-model",
        help="Model override for the challenger. Defaults to the provider model in settings.",
    )
    anchor_benchmark_parser.add_argument(
        "--anchor",
        dest="anchors",
        action="append",
        help="Anchor name to include. Repeat to select multiple anchors. Defaults to the full anchor ladder.",
    )
    anchor_benchmark_parser.add_argument("--games-per-anchor", type=int, default=2)
    anchor_benchmark_parser.add_argument("--max-plies", type=int)
    anchor_benchmark_parser.add_argument(
        "--max-correction-attempts",
        type=int,
        default=1,
        help="Number of retry attempts after a deterministically rejected move.",
    )
    anchor_benchmark_parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Disable post-move Stockfish analysis persistence during the benchmark.",
    )
    anchor_benchmark_parser.add_argument(
        "--skip-rating",
        action="store_true",
        help="Skip automatic Elo updates after each completed game.",
    )
    anchor_benchmark_parser.add_argument(
        "--db-path", help="Override the SQLite database path."
    )
    anchor_benchmark_parser.add_argument("--json", action="store_true")

    create_tournament_parser = subparsers.add_parser(
        "create-tournament",
        help="Create a persistent tournament with stored roster entries and pairings.",
    )
    create_tournament_parser.add_argument("--name", required=True)
    create_tournament_parser.add_argument(
        "--format",
        choices=["round-robin", "anchor-benchmark"],
        required=True,
    )
    create_tournament_parser.add_argument(
        "--player",
        dest="players",
        action="append",
        help="Player spec in the form provider:model. Repeat for round-robin tournaments.",
    )
    create_tournament_parser.add_argument(
        "--single-round",
        action="store_true",
        help="Use a single round-robin instead of home-and-away pairings.",
    )
    create_tournament_parser.add_argument("--challenger-provider")
    create_tournament_parser.add_argument("--challenger-model")
    create_tournament_parser.add_argument(
        "--anchor",
        dest="anchors",
        action="append",
        help="Anchor name for anchor-benchmark tournaments. Repeat to select multiple anchors.",
    )
    create_tournament_parser.add_argument("--games-per-anchor", type=int, default=2)
    create_tournament_parser.add_argument("--notes")
    create_tournament_parser.add_argument("--db-path")
    create_tournament_parser.add_argument("--json", action="store_true")

    list_tournaments_parser = subparsers.add_parser(
        "list-tournaments",
        help="List persisted tournaments.",
    )
    list_tournaments_parser.add_argument("--db-path")
    list_tournaments_parser.add_argument("--status")
    list_tournaments_parser.add_argument("--limit", type=int, default=20)
    list_tournaments_parser.add_argument("--json", action="store_true")

    inspect_tournament_parser = subparsers.add_parser(
        "inspect-tournament",
        help="Inspect one persisted tournament, including pairings and standings.",
    )
    inspect_tournament_parser.add_argument("tournament_id", type=int)
    inspect_tournament_parser.add_argument("--db-path")
    inspect_tournament_parser.add_argument("--json", action="store_true")

    export_tournament_parser = subparsers.add_parser(
        "export-tournament",
        help="Export one tournament as JSON or Markdown.",
    )
    export_tournament_parser.add_argument("tournament_id", type=int)
    export_tournament_parser.add_argument("--db-path")
    export_tournament_parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
    )
    export_tournament_parser.add_argument("--output")

    run_tournament_parser = subparsers.add_parser(
        "run-tournament",
        help="Run or resume a persisted tournament.",
    )
    run_tournament_parser.add_argument("tournament_id", type=int)
    run_tournament_parser.add_argument("--db-path")
    run_tournament_parser.add_argument("--max-matches", type=int)
    run_tournament_parser.add_argument("--max-plies", type=int)
    run_tournament_parser.add_argument(
        "--max-correction-attempts",
        type=int,
        default=1,
    )
    run_tournament_parser.add_argument(
        "--include-failed",
        action="store_true",
        help="Retry failed pairings as well as pending pairings.",
    )
    run_tournament_parser.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Disable post-move Stockfish analysis persistence during tournament execution.",
    )
    run_tournament_parser.add_argument(
        "--skip-rating",
        action="store_true",
        help="Skip automatic rating updates after completed tournament games.",
    )
    run_tournament_parser.add_argument("--json", action="store_true")

    pause_tournament_parser = subparsers.add_parser(
        "pause-tournament",
        help="Pause a persisted tournament without modifying pairings.",
    )
    pause_tournament_parser.add_argument("tournament_id", type=int)
    pause_tournament_parser.add_argument("--db-path")
    pause_tournament_parser.add_argument("--json", action="store_true")

    elo_parser = subparsers.add_parser(
        "elo-preview", help="Preview an Elo update for two ratings."
    )
    elo_parser.add_argument("--player-rating", type=float, required=True)
    elo_parser.add_argument("--opponent-rating", type=float, required=True)
    elo_parser.add_argument(
        "--result",
        choices=["win", "draw", "loss"],
        required=True,
    )
    elo_parser.add_argument("--json", action="store_true")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = AppSettings.from_env()

    if args.command == "settings":
        return _run_settings(args, settings)

    if args.command == "play":
        return _run_play(args, settings)

    if args.command == "list-games":
        return _run_list_games(args, settings)

    if args.command == "inspect-game":
        return _run_inspect_game(args, settings)

    if args.command == "replay":
        return _run_replay(args, settings)

    if args.command == "export-game":
        return _run_export_game(args, settings)

    if args.command == "diagnose-provider":
        return _run_diagnose_provider(args, settings)

    if args.command == "diagnose-stockfish":
        return _run_diagnose_stockfish(args, settings)

    if args.command == "list-anchors":
        return _run_list_anchors(args)

    if args.command == "list-ratings":
        return _run_list_ratings(args, settings)

    if args.command == "chess-index":
        return _run_chess_index(args, settings)

    if args.command == "rating-history":
        return _run_rating_history(args, settings)

    if args.command == "rate-game":
        return _run_rate_game(args, settings)

    if args.command == "run-anchor-benchmark":
        return _run_anchor_benchmark(args, settings)

    if args.command == "create-tournament":
        return _run_create_tournament(args, settings)

    if args.command == "list-tournaments":
        return _run_list_tournaments(args, settings)

    if args.command == "inspect-tournament":
        return _run_inspect_tournament(args, settings)

    if args.command == "export-tournament":
        return _run_export_tournament(args, settings)

    if args.command == "run-tournament":
        return _run_run_tournament(args, settings)

    if args.command == "pause-tournament":
        return _run_pause_tournament(args, settings)

    if args.command == "elo-preview":
        return _run_elo_preview(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


def _run_play(args: argparse.Namespace, settings: AppSettings) -> int:
    white_provider_name = args.white_provider or settings.default_provider.value
    black_provider_name = args.black_provider or white_provider_name

    white_provider = build_provider(
        white_provider_name, settings, model=args.white_model
    )
    black_provider = build_provider(
        black_provider_name, settings, model=args.black_model
    )

    repository = _build_repository(args, settings)
    analysis_engine = None
    if not args.skip_analysis:
        analysis_engine = StockfishEngine(
            path=settings.stockfish.path,
            depth=settings.stockfish.depth,
            multipv=settings.stockfish.multipv,
            movetime_ms=settings.stockfish.movetime_ms,
        )
    runner = GameRunner(
        white_provider=white_provider,
        black_provider=black_provider,
        repository=repository,
        max_plies=args.max_plies or settings.max_plies,
        move_temperature=settings.move_temperature,
        max_output_tokens=settings.max_output_tokens,
        log_raw_response_json=settings.log_raw_response_json,
        max_correction_attempts=args.max_correction_attempts,
        analysis_engine=analysis_engine,
    )
    result = runner.play(initial_fen=args.fen)

    if not args.quiet:
        payload = {
            "game_id": result.game_id,
            "status": result.status,
            "result": result.result,
            "termination_reason": result.termination_reason,
            "moves": list(result.moves),
        }
        print(json.dumps(payload, indent=2))

    return 0


def _run_settings(args: argparse.Namespace, settings: AppSettings) -> int:
    payload = settings.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    return 0


def _run_list_games(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    games = repository.list_games(limit=args.limit)
    if args.json:
        print(json.dumps(games, indent=2))
        return 0

    if not games:
        print("No games recorded.")
        return 0

    for game in games:
        print(
            f"#{game['id']} {game['white_model']} vs {game['black_model']} "
            f"[{game['status']}] result={game['result'] or '*'} "
            f"reason={game['termination_reason'] or '-'}"
        )
    return 0


def _run_inspect_game(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    bundle = _game_bundle_for(repository, args.game_id)
    if args.json:
        print(json.dumps(bundle, indent=2))
    else:
        print(json.dumps(bundle, indent=2))
    return 0


def _run_replay(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    bundle = _game_bundle_for(repository, args.game_id)
    if args.json:
        print(json.dumps(bundle, indent=2))
        return 0

    print(render_move_list(bundle["accepted_turns"]))
    return 0


def _run_export_game(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    game = _require_game(repository, args.game_id)
    turns = repository.list_turns(args.game_id)
    hallucinations = repository.list_hallucinations(args.game_id)
    engine_analyses = repository.list_engine_analyses(args.game_id)

    if args.format == "pgn":
        payload = build_game_bundle(game, turns, hallucinations, engine_analyses)["pgn"]
    else:
        payload = export_game_json(game, turns, hallucinations, engine_analyses)

    if args.output:
        Path(args.output).write_text(payload + ("" if payload.endswith("\n") else "\n"))
    else:
        print(payload)
    return 0


def _run_diagnose_provider(args: argparse.Namespace, settings: AppSettings) -> int:
    provider_name = args.provider or settings.default_provider.value
    provider = build_provider(provider_name, settings, model=args.model)
    report = provider.health_check()
    payload = {
        "provider_name": report.provider_name,
        "model": report.model,
        "is_healthy": report.is_healthy,
        "latency_ms": report.latency_ms,
        "model_available": report.model_available,
        "error_code": report.error_code.value if report.error_code else None,
        "error_message": report.error_message,
        "capabilities": asdict(report.capabilities),
        "metadata": report.metadata,
    }
    print(json.dumps(payload, indent=2))
    return 0 if report.is_healthy and report.model_available is not False else 1


def _run_diagnose_stockfish(args: argparse.Namespace, settings: AppSettings) -> int:
    engine = StockfishEngine(
        path=args.engine_path or settings.stockfish.path,
        depth=args.depth or settings.stockfish.depth,
        multipv=args.multipv or settings.stockfish.multipv,
        movetime_ms=settings.stockfish.movetime_ms,
    )
    health = engine.health_check()
    payload: dict[str, Any] = {
        "engine_path": health.engine_path,
        "is_healthy": health.is_healthy,
        "engine_name": health.engine_name,
        "error_message": health.error_message,
        "metadata": health.metadata,
    }
    if health.is_healthy and args.fen:
        payload["analysis"] = [
            {
                "multipv_rank": row.multipv_rank,
                "best_move_uci": row.best_move_uci,
                "best_move_san": row.best_move_san,
                "score_cp": row.score_cp,
                "score_mate": row.score_mate,
                "pv_uci": list(row.pv_uci),
                "pv_san": list(row.pv_san),
            }
            for row in engine.analyze(
                args.fen,
                depth=args.depth,
                multipv=args.multipv,
            )
        ]
    print(json.dumps(payload, indent=2))
    return 0 if health.is_healthy else 1


def _run_list_anchors(args: argparse.Namespace) -> int:
    anchors = default_engine_anchors()
    payload = [
        {
            "name": anchor.name,
            "starting_rating": anchor.starting_rating,
            "description": anchor.description,
            "identity": {
                "provider": anchor.identity.provider,
                "model": anchor.identity.model,
                "runtime": anchor.identity.runtime,
                "prompt_profile": anchor.identity.prompt_profile,
                "slug": anchor.identity.slug,
            },
        }
        for anchor in anchors
    ]
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for anchor in anchors:
            print(
                f"{anchor.name} rating={anchor.starting_rating:.0f} "
                f"runtime={anchor.identity.runtime} "
                f"slug={anchor.identity.slug}"
            )
    return 0


def _run_list_ratings(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    ratings = repository.list_latest_ratings(limit=args.limit)
    if args.json:
        print(json.dumps(ratings, indent=2))
        return 0

    if not ratings:
        print("No ratings recorded.")
        return 0

    for row in ratings:
        print(
            f"{row['competitor_slug']} rating={row['rating']:.1f} "
            f"games={row['games_played']} provisional={row['provisional']}"
        )
    return 0


def _run_chess_index(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    snapshot = build_chess_index_snapshot(
        repository,
        limit=args.limit,
        minimum_games=args.minimum_games,
        include_provisional=args.include_provisional,
    )
    if args.format == "markdown":
        payload = render_chess_index_markdown(snapshot)
    else:
        payload = json.dumps(snapshot.to_dict(), indent=2)
    _write_or_print(payload, output_path=args.output)
    return 0


def _run_rating_history(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    history = repository.list_rating_history(args.competitor_slug)
    if args.json:
        print(json.dumps(history, indent=2))
        return 0

    if not history:
        print("No rating history recorded.")
        return 0

    for row in history:
        print(
            f"#{row['id']} rating={row['rating']:.1f} games={row['games_played']} "
            f"result={row['source_result'] or '-'} game_id={row['source_game_id'] or '-'}"
        )
    return 0


def _run_rate_game(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    update = rate_recorded_game(
        repository,
        args.game_id,
        white_runtime=args.white_runtime,
        black_runtime=args.black_runtime,
        white_prompt_profile=args.white_prompt_profile,
        black_prompt_profile=args.black_prompt_profile,
        white_quantization=args.white_quantization,
        black_quantization=args.black_quantization,
        white_hardware_class=args.white_hardware_class,
        black_hardware_class=args.black_hardware_class,
        white_revision=args.white_revision,
        black_revision=args.black_revision,
    )
    payload = {
        "game_id": args.game_id,
        "result": update.result,
        "white": {
            "slug": update.white_after.competitor.slug,
            "before": update.white_before.rating,
            "after": update.white_after.rating,
            "games_played": update.white_after.games_played,
            "provisional": update.white_after.provisional,
        },
        "black": {
            "slug": update.black_after.competitor.slug,
            "before": update.black_before.rating,
            "after": update.black_after.rating,
            "games_played": update.black_after.games_played,
            "provisional": update.black_after.provisional,
        },
    }
    print(json.dumps(payload, indent=2))
    return 0


def _run_anchor_benchmark(args: argparse.Namespace, settings: AppSettings) -> int:
    challenger_provider = args.challenger_provider or settings.default_provider.value
    challenger_model = args.challenger_model or settings.model_for(challenger_provider)
    repository = _build_repository(args, settings)
    summary = run_anchor_benchmark(
        challenger=PlayerSpec(
            provider_name=challenger_provider,
            model=challenger_model,
        ),
        settings=settings,
        repository=repository,
        anchor_names=args.anchors,
        games_per_anchor=args.games_per_anchor,
        max_plies=args.max_plies,
        max_correction_attempts=args.max_correction_attempts,
        record_engine_analysis=not args.skip_analysis,
        auto_rate=not args.skip_rating,
    )
    matches_payload: list[dict[str, Any]] = [
        {
            "match_number": item.match.match_number,
            "round_number": item.match.round_number,
            "tag": item.match.tag,
            "white": item.match.white.label,
            "black": item.match.black.label,
            "game_id": item.game.game_id,
            "status": item.game.status,
            "result": item.game.result,
            "termination_reason": item.game.termination_reason,
            "rating_update": (
                {
                    "white_after": item.rating_update.white_after.rating,
                    "black_after": item.rating_update.black_after.rating,
                    "white_slug": item.rating_update.white_after.competitor.slug,
                    "black_slug": item.rating_update.black_after.competitor.slug,
                }
                if item.rating_update is not None
                else None
            ),
        }
        for item in summary.matches
    ]
    payload = {
        "scheduled_matches": len(summary.matches),
        "completed_matches": len(summary.matches),
        "matches": matches_payload,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    for item in matches_payload:
        print(
            f"match {item['match_number']}: {item['white']} vs {item['black']} "
            f"game_id={item['game_id']} result={item['result'] or '*'} "
            f"reason={item['termination_reason'] or '-'}"
        )
    return 0


def _run_create_tournament(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    if args.format == "round-robin":
        players = _parse_player_specs(args.players or [])
        tournament_id = create_round_robin_tournament(
            repository,
            name=args.name,
            players=players,
            double_round_robin=not args.single_round,
            notes=args.notes,
        )
    else:
        challenger_provider = (
            args.challenger_provider or settings.default_provider.value
        )
        challenger_model = args.challenger_model or settings.model_for(
            challenger_provider
        )
        tournament_id = create_anchor_tournament(
            repository,
            name=args.name,
            challenger=PlayerSpec(
                provider_name=challenger_provider,
                model=challenger_model,
            ),
            anchor_names=args.anchors,
            games_per_anchor=args.games_per_anchor,
            notes=args.notes,
        )

    tournament = _require_tournament(repository, tournament_id)
    payload = _tournament_bundle(repository, tournament)
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(
        f"Created tournament #{tournament_id} {tournament['name']} "
        f"[{tournament['format']}] status={tournament['status']}"
    )
    return 0


def _run_list_tournaments(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    tournaments = repository.list_tournaments(status=args.status, limit=args.limit)
    if args.json:
        print(json.dumps(tournaments, indent=2))
        return 0

    if not tournaments:
        print("No tournaments recorded.")
        return 0

    for tournament in tournaments:
        print(
            f"#{tournament['id']} {tournament['name']} "
            f"[{tournament['format']}] status={tournament['status']}"
        )
    return 0


def _run_inspect_tournament(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    tournament = _require_tournament(repository, args.tournament_id)
    payload = _tournament_bundle(repository, tournament)
    print(json.dumps(payload, indent=2))
    return 0


def _run_export_tournament(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    _require_tournament(repository, args.tournament_id)
    if args.format == "markdown":
        payload = render_tournament_markdown(repository, args.tournament_id)
    else:
        payload = export_tournament_json(repository, args.tournament_id)
    _write_or_print(payload, output_path=args.output)
    return 0


def _run_run_tournament(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    summary = run_tournament(
        repository,
        tournament_id=args.tournament_id,
        settings=settings,
        max_matches=args.max_matches,
        max_plies=args.max_plies,
        max_correction_attempts=args.max_correction_attempts,
        record_engine_analysis=not args.skip_analysis,
        auto_rate=not args.skip_rating,
        include_failed=args.include_failed,
    )
    payload = {
        "tournament_id": summary.tournament_id,
        "status": summary.status,
        "completed_pairings": summary.completed_pairings,
        "pending_pairings": summary.pending_pairings,
        "failed_pairings": summary.failed_pairings,
        "processed": [
            {
                "pairing_id": item.pairing_id,
                "match_number": item.match_number,
                "round_number": item.round_number,
                "white": item.white_label,
                "black": item.black_label,
                "status": item.status,
                "game_id": item.game.game_id if item.game is not None else None,
                "result": item.game.result if item.game is not None else None,
                "termination_reason": (
                    item.game.termination_reason if item.game is not None else None
                ),
                "rating_update": (
                    {
                        "white_after": item.rating_update.white_after.rating,
                        "black_after": item.rating_update.black_after.rating,
                        "white_slug": item.rating_update.white_after.competitor.slug,
                        "black_slug": item.rating_update.black_after.competitor.slug,
                    }
                    if item.rating_update is not None
                    else None
                ),
                "error_message": item.error_message,
            }
            for item in summary.processed
        ],
        "standings": list(summary.standings),
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(
        f"Tournament #{summary.tournament_id} status={summary.status} "
        f"completed={summary.completed_pairings} pending={summary.pending_pairings} "
        f"failed={summary.failed_pairings}"
    )
    return 0


def _run_pause_tournament(args: argparse.Namespace, settings: AppSettings) -> int:
    repository = _build_repository(args, settings)
    pause_tournament(repository, args.tournament_id)
    tournament = _require_tournament(repository, args.tournament_id)
    payload = {
        "tournament_id": args.tournament_id,
        "status": tournament["status"],
    }
    print(json.dumps(payload, indent=2))
    return 0


def _run_elo_preview(args: argparse.Namespace) -> int:
    player = RatingSnapshot(
        competitor=default_engine_anchors()[0].identity,
        rating=args.player_rating,
        provisional=False,
    )
    opponent = RatingSnapshot(
        competitor=default_engine_anchors()[1].identity,
        rating=args.opponent_rating,
        provisional=False,
    )
    result_map = {
        "win": EloMatchResult.WIN,
        "draw": EloMatchResult.DRAW,
        "loss": EloMatchResult.LOSS,
    }
    result = result_map[args.result]
    update = apply_elo_result(player, opponent, result)
    payload = {
        "player_rating": player.rating,
        "opponent_rating": opponent.rating,
        "expected_score": update.expected_score,
        "actual_score": update.actual_score,
        "new_rating": update.new_rating,
        "new_games_played": update.new_games_played,
        "provisional": update.provisional,
    }
    print(json.dumps(payload, indent=2))
    return 0


def _build_repository(
    args: argparse.Namespace, settings: AppSettings
) -> SQLiteRepository:
    repository = SQLiteRepository(Path(args.db_path or settings.database_path))
    repository.initialize()
    return repository


def _write_or_print(payload: str, *, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_text(payload + ("" if payload.endswith("\n") else "\n"))
        return
    print(payload)


def _game_bundle_for(repository: SQLiteRepository, game_id: int) -> dict[str, Any]:
    game = _require_game(repository, game_id)
    turns = repository.list_turns(game_id)
    hallucinations = repository.list_hallucinations(game_id)
    engine_analyses = repository.list_engine_analyses(game_id)
    return build_game_bundle(game, turns, hallucinations, engine_analyses)


def _tournament_bundle(
    repository: SQLiteRepository,
    tournament: dict[str, Any],
) -> dict[str, Any]:
    tournament_id = int(tournament["id"])
    players = repository.list_tournament_players(tournament_id)
    pairings = repository.list_tournament_pairings(tournament_id)
    standings = repository.compute_tournament_standings(tournament_id)
    return {
        "tournament": tournament,
        "players": players,
        "pairings": pairings,
        "standings": standings,
    }


def _require_game(repository: SQLiteRepository, game_id: int) -> dict[str, Any]:
    game = repository.get_game(game_id)
    if game is None:
        raise SystemExit(f"Game {game_id} was not found.")
    return game


def _require_tournament(
    repository: SQLiteRepository,
    tournament_id: int,
) -> dict[str, Any]:
    tournament = repository.get_tournament(tournament_id)
    if tournament is None:
        raise SystemExit(f"Tournament {tournament_id} was not found.")
    return tournament


def _parse_player_specs(values: Sequence[str]) -> list[PlayerSpec]:
    players: list[PlayerSpec] = []
    for raw in values:
        provider_name, separator, model = raw.partition(":")
        if not separator or not provider_name.strip() or not model.strip():
            raise SystemExit(
                f"Invalid player spec {raw!r}. Expected the form provider:model."
            )
        players.append(
            PlayerSpec(
                provider_name=provider_name.strip(),
                model=model.strip(),
            )
        )
    if len(players) < 2:
        raise SystemExit("At least two --player values are required.")
    return players


if __name__ == "__main__":
    raise SystemExit(main())
