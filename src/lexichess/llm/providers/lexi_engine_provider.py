from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from lexichess.llm.base import (
    MoveProvider,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCode,
    ProviderHealthReport,
)
from lexichess.llm.types import MoveRequest, ProviderResponse


class LexiEngineProvider(MoveProvider):
    provider_name = "lexi_engine"

    def __init__(
        self,
        *,
        path: str,
        profile: str,
        depth: int = 3,
    ) -> None:
        self.path = path
        self.model = profile
        self.depth = max(depth, 1)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_sync_requests=True,
            supports_system_instructions=False,
            supports_model_listing=True,
            supports_health_checks=True,
            local_only=True,
        )

    def health_check(self) -> ProviderHealthReport:
        started_at = time.perf_counter()
        try:
            payload = self._run_command("health")
            profiles = tuple(
                str(profile.get("name"))
                for profile in payload.get("profiles", [])
                if isinstance(profile, dict) and isinstance(profile.get("name"), str)
            )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            return ProviderHealthReport(
                provider_name=self.provider_name,
                model=self.model,
                is_healthy=True,
                latency_ms=latency_ms,
                model_available=self.model in profiles,
                capabilities=self.capabilities(),
                metadata={
                    "path": self.path,
                    "version": payload.get("version"),
                    "available_models": profiles,
                    "depth": self.depth,
                },
            )
        except ProviderError as exc:
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            return ProviderHealthReport(
                provider_name=self.provider_name,
                model=self.model,
                is_healthy=False,
                latency_ms=latency_ms,
                model_available=None,
                error_code=exc.code,
                error_message=str(exc),
                capabilities=self.capabilities(),
                metadata={"path": self.path, "depth": self.depth},
            )

    def request_move(self, request: MoveRequest) -> ProviderResponse:
        started_at = time.perf_counter()
        payload = self._run_command(
            "move",
            "--fen",
            request.fen,
            "--profile",
            self.model,
            "--depth",
            str(self.depth),
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        best_move_uci = payload.get("best_move_uci")
        if not isinstance(best_move_uci, str) or not best_move_uci.strip():
            raise ProviderError(
                "Lexi engine did not return a best move.",
                code=ProviderErrorCode.INVALID_RESPONSE,
            )

        return ProviderResponse(
            provider=self.provider_name,
            model=self.model,
            output_text=best_move_uci.strip(),
            raw_response=payload,
            latency_ms=latency_ms,
            finish_reason="engine_move",
        )

    def _run_command(self, *args: str) -> dict[str, Any]:
        executable = _resolve_engine_path(self.path)
        try:
            completed = subprocess.run(
                [str(executable), *args],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise ProviderError(
                f"Unable to launch Lexi engine: {exc}",
                code=ProviderErrorCode.MODEL_UNAVAILABLE,
            ) from exc

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            raise ProviderError(
                f"Lexi engine command failed: {stderr or 'unknown error'}",
                code=ProviderErrorCode.MODEL_UNAVAILABLE,
            )

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"Lexi engine returned invalid JSON: {exc}",
                code=ProviderErrorCode.INVALID_RESPONSE,
            ) from exc

        if not isinstance(payload, dict):
            raise ProviderError(
                "Lexi engine returned a non-object JSON payload.",
                code=ProviderErrorCode.INVALID_RESPONSE,
            )
        return payload


def _resolve_engine_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.exists():
        return candidate

    default_candidates = {
        Path("engine/rust_engine/target/release/lexichess-engine"),
        Path("engine/rust_engine/target/debug/lexichess-engine"),
    }
    if candidate.is_absolute() or candidate not in default_candidates:
        return candidate

    release_candidate = (
        Path(__file__).resolve().parents[4]
        / "engine"
        / "rust_engine"
        / "target"
        / "release"
        / "lexichess-engine"
    )
    if release_candidate.exists():
        return release_candidate

    debug_candidate = (
        Path(__file__).resolve().parents[4]
        / "engine"
        / "rust_engine"
        / "target"
        / "debug"
        / "lexichess-engine"
    )
    if debug_candidate.exists():
        return debug_candidate

    return candidate
