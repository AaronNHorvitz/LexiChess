from __future__ import annotations

from lexichess.config import AppSettings
from lexichess.interactive.showmatch import (
    DeterministicShowmatchScriptService,
    ProviderBackedShowmatchScriptService,
    build_showmatch_script_service,
)
from lexichess.llm.base import MoveProvider, ProviderCapabilities, ProviderHealthReport
from lexichess.llm.types import MoveRequest, ProviderResponse


class FakeShowmatchProvider(MoveProvider):
    def __init__(
        self,
        *,
        provider_name: str = "ollama",
        model: str = "gemma4:latest",
        message: str = "Arena Booth is losing its mind over that move.",
        supports_system_instructions: bool = True,
    ) -> None:
        self.provider_name = provider_name
        self.model = model
        self._message = message
        self._supports_system_instructions = supports_system_instructions

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_sync_requests=True,
            supports_system_instructions=self._supports_system_instructions,
            supports_health_checks=True,
            local_only=True,
        )

    def health_check(self) -> ProviderHealthReport:
        return ProviderHealthReport(
            provider_name=self.provider_name,
            model=self.model,
            is_healthy=True,
            model_available=True,
            capabilities=self.capabilities(),
        )

    def request_move(self, request: MoveRequest) -> ProviderResponse:
        assert request.prompt_kind is not None
        assert request.prompt_version is not None
        return ProviderResponse(
            provider=self.provider_name,
            model=self.model,
            output_text=self._message,
            raw_response={"text": self._message},
            latency_ms=1,
        )


def _provider_name(value: object) -> str:
    return getattr(value, "value", str(value))


def test_provider_backed_showmatch_service_uses_model_output() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_SHOWMATCH_SCRIPT_PROVIDER": "ollama",
            "LEXICHESS_SHOWMATCH_SCRIPT_MODEL": "gemma4:latest",
        },
        dotenv_path=None,
    )

    service = ProviderBackedShowmatchScriptService(
        settings,
        provider_builder=lambda provider, settings, *, model=None: FakeShowmatchProvider(
            provider_name=_provider_name(provider),
            model=model or settings.showmatch_scripts.model,
            message="Arena Booth says this opening already has bad intentions.",
        ),
    )

    payload = service.pregame_intro(
        game_id=1,
        white_player="Qwen Hero",
        black_player="Qwen Villain",
    )

    assert payload is not None
    assert payload["source"] == "model"
    assert payload["provider"] == "ollama"
    assert payload["model"] == "gemma4:latest"
    assert payload["category"] == "pregame"
    assert payload["message"].startswith("Arena Booth says")


def test_showmatch_service_falls_back_when_provider_cannot_support_role() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_SHOWMATCH_SCRIPT_PROVIDER": "stockfish",
            "LEXICHESS_SHOWMATCH_SCRIPT_MODEL": "stockfish_club",
        },
        dotenv_path=None,
    )

    service = build_showmatch_script_service(
        settings,
        provider_builder=lambda provider, settings, *, model=None: FakeShowmatchProvider(
            provider_name=_provider_name(provider),
            model=model or settings.showmatch_scripts.model,
            supports_system_instructions=False,
        ),
    )

    payload = service.finish(
        game_id=1,
        result="1/2-1/2",
        termination_reason="stalemate",
        winner=None,
        loser=None,
        fen="startpos",
    )

    assert payload is not None
    assert payload["source"] == "fallback"
    assert payload["provider"] == "deterministic"
    assert payload["category"] == "finish"
    assert "draw" in payload["message"].lower()


def test_deterministic_showmatch_service_builds_hype_payload() -> None:
    service = DeterministicShowmatchScriptService(speaker_name="Arena Booth")

    payload = service.midgame_hype(
        game_id=1,
        color="white",
        speaker="Qwen Hero",
        opponent="Qwen Villain",
        move="Qxh7+",
        ply=17,
        tags=("capture", "check"),
        fen="fen",
    )

    assert payload["speaker"] == "Arena Booth"
    assert payload["category"] == "hype"
    assert payload["move"] == "Qxh7+"
    assert payload["tags"] == ["capture", "check"]
