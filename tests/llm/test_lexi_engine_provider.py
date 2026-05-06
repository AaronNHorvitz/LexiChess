from __future__ import annotations

import stat
import textwrap
from pathlib import Path

import pytest

from lexichess.llm.base import ProviderError, ProviderErrorCode
from lexichess.llm.providers import LexiEngineProvider
from lexichess.llm.types import MoveRequest


def _write_engine_script(tmp_path: Path, body: str) -> Path:
    script_path = tmp_path / "fake-engine"
    script_path.write_text(body)
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
    return script_path


def test_lexi_engine_provider_runs_move_command(tmp_path: Path) -> None:
    script_path = _write_engine_script(
        tmp_path,
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import sys

            if sys.argv[1] == "move":
                profile = sys.argv[sys.argv.index("--profile") + 1]
                depth = int(sys.argv[sys.argv.index("--depth") + 1])
                print(json.dumps({
                    "best_move_uci": "e2e4",
                    "profile": profile,
                    "depth": depth,
                    "score": 17,
                }))
            else:
                print(json.dumps({"status": "ok", "version": "0.1.0", "profiles": []}))
            """
        ),
    )
    provider = LexiEngineProvider(
        path=str(script_path),
        profile="aggressive",
        depth=4,
    )

    response = provider.request_move(
        MoveRequest(
            game_id=1,
            move_number=1,
            color="white",
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            prompt="Choose a move.",
            instructions="Return one move.",
            legal_moves=("e4", "d4"),
        )
    )

    assert response.output_text == "e2e4"
    assert response.raw_response == {
        "best_move_uci": "e2e4",
        "profile": "aggressive",
        "depth": 4,
        "score": 17,
    }
    assert response.finish_reason == "engine_move"


def test_lexi_engine_provider_health_check_reports_profiles(tmp_path: Path) -> None:
    script_path = _write_engine_script(
        tmp_path,
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import sys

            if sys.argv[1] == "health":
                print(json.dumps({
                    "status": "ok",
                    "version": "0.1.0",
                    "profiles": [
                        {"name": "balanced", "description": "Balanced style"},
                        {"name": "aggressive", "description": "Aggressive style"},
                    ],
                }))
            else:
                print(json.dumps({"best_move_uci": "e2e4"}))
            """
        ),
    )
    provider = LexiEngineProvider(
        path=str(script_path),
        profile="aggressive",
        depth=3,
    )

    report = provider.health_check()

    assert report.is_healthy is True
    assert report.model_available is True
    assert report.metadata["available_models"] == ("balanced", "aggressive")


def test_lexi_engine_provider_surfaces_invalid_json(tmp_path: Path) -> None:
    script_path = _write_engine_script(
        tmp_path,
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            print("not json")
            """
        ),
    )
    provider = LexiEngineProvider(
        path=str(script_path),
        profile="balanced",
        depth=2,
    )

    with pytest.raises(ProviderError) as exc_info:
        provider.request_move(
            MoveRequest(
                game_id=None,
                move_number=1,
                color="white",
                fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                prompt="Choose a move.",
                instructions="Return one move.",
                legal_moves=("e4",),
            )
        )

    assert exc_info.value.code is ProviderErrorCode.INVALID_RESPONSE


def test_lexi_engine_provider_handles_missing_binary(tmp_path: Path) -> None:
    provider = LexiEngineProvider(
        path=str(tmp_path / "missing-engine"),
        profile="balanced",
        depth=3,
    )

    report = provider.health_check()

    assert report.is_healthy is False
    assert report.error_code is ProviderErrorCode.MODEL_UNAVAILABLE
