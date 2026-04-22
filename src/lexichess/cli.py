from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from lexichess.config import AppSettings, ProviderName
from lexichess.llm.registry import build_provider
from lexichess.storage.repository import SQLiteRepository
from lexichess.tournament.runner import GameRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LexiChess MVP CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

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
    play_parser.add_argument("--db-path", help="Override the SQLite database path.")
    play_parser.add_argument(
        "--quiet", action="store_true", help="Suppress the JSON game summary output."
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = AppSettings.from_env()

    if args.command == "play":
        return _run_play(args, settings)

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

    repository = SQLiteRepository(Path(args.db_path or settings.database_path))
    runner = GameRunner(
        white_provider=white_provider,
        black_provider=black_provider,
        repository=repository,
        max_plies=args.max_plies or settings.max_plies,
        move_temperature=settings.move_temperature,
        max_output_tokens=settings.max_output_tokens,
        log_raw_response_json=settings.log_raw_response_json,
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


if __name__ == "__main__":
    raise SystemExit(main())
