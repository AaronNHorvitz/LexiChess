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
    default_engine_anchors,
    identity_from_game,
    rate_completed_game,
)
from lexichess.llm.registry import build_provider
from lexichess.storage.repository import SQLiteRepository
from lexichess.tournament.replay import (
    build_game_bundle,
    export_game_json,
    render_move_list,
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

    if args.command == "rating-history":
        return _run_rating_history(args, settings)

    if args.command == "rate-game":
        return _run_rate_game(args, settings)

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
    runner = GameRunner(
        white_provider=white_provider,
        black_provider=black_provider,
        repository=repository,
        max_plies=args.max_plies or settings.max_plies,
        move_temperature=settings.move_temperature,
        max_output_tokens=settings.max_output_tokens,
        log_raw_response_json=settings.log_raw_response_json,
        max_correction_attempts=args.max_correction_attempts,
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

    if args.format == "pgn":
        payload = build_game_bundle(game, turns, hallucinations)["pgn"]
    else:
        payload = export_game_json(game, turns, hallucinations)

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
    game = _require_game(repository, args.game_id)
    turns = repository.list_turns(args.game_id)
    result = game.get("result")
    if not isinstance(result, str) or result not in {"1-0", "0-1", "1/2-1/2"}:
        raise SystemExit(
            f"Game {args.game_id} does not have a rateable result. "
            "Expected one of 1-0, 0-1, or 1/2-1/2."
        )

    white_identity = identity_from_game(
        game,
        turns,
        color="white",
        runtime=args.white_runtime,
        prompt_profile=args.white_prompt_profile,
        quantization=args.white_quantization,
        hardware_class=args.white_hardware_class,
        revision=args.white_revision,
    )
    black_identity = identity_from_game(
        game,
        turns,
        color="black",
        runtime=args.black_runtime,
        prompt_profile=args.black_prompt_profile,
        quantization=args.black_quantization,
        hardware_class=args.black_hardware_class,
        revision=args.black_revision,
    )

    update = rate_completed_game(
        repository,
        white=white_identity,
        black=black_identity,
        result=result,
        source_game_id=args.game_id,
    )
    payload = {
        "game_id": args.game_id,
        "result": result,
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


def _game_bundle_for(repository: SQLiteRepository, game_id: int) -> dict[str, Any]:
    game = _require_game(repository, game_id)
    turns = repository.list_turns(game_id)
    hallucinations = repository.list_hallucinations(game_id)
    return build_game_bundle(game, turns, hallucinations)


def _require_game(repository: SQLiteRepository, game_id: int) -> dict[str, Any]:
    game = repository.get_game(game_id)
    if game is None:
        raise SystemExit(f"Game {game_id} was not found.")
    return game


if __name__ == "__main__":
    raise SystemExit(main())
