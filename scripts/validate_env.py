from __future__ import annotations

import argparse
import json

from lexichess.config import AppSettings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate LexiChess environment configuration."
    )
    parser.add_argument(
        "--dotenv-path",
        default=".env",
        help="Path to a dotenv file. Use an empty string to skip dotenv loading.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the resolved settings as JSON.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    dotenv_path = args.dotenv_path or None
    settings = AppSettings.from_env(dotenv_path=dotenv_path)

    payload = settings.to_dict()
    ollama = payload["ollama"]
    assert isinstance(ollama, dict)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("LexiChess environment is valid.")
        print(f"Provider: {payload['default_provider']}")
        print(f"Profile: {payload['environment_profile']}")
        print(f"Database: {payload['database_path']}")
        print(f"Ollama host: {ollama['host']}")
        print(f"Ollama model: {ollama['model']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
