from __future__ import annotations

from lexichess.config import AppSettings
from lexichess.interactive.banter import (
    DeterministicBanterService,
    ProviderBackedBanterService,
    build_banter_service,
)
from lexichess.llm.base import MoveProvider, ProviderCapabilities, ProviderHealthReport
from lexichess.llm.types import MoveRequest, ProviderResponse


class FakeBanterProvider(MoveProvider):
    def __init__(
        self,
        *,
        provider_name: str = "ollama",
        model: str = "qwen3:8b",
        message: str = "That bishop came screaming in and your opponent still has to look at it.",
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


def test_provider_backed_banter_service_uses_model_output() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_BANTER_PROVIDER": "ollama",
            "LEXICHESS_BANTER_MODEL": "qwen3:14b",
        },
        dotenv_path=None,
    )

    service = ProviderBackedBanterService(
        settings,
        provider_builder=lambda provider, settings, *, model=None: FakeBanterProvider(
            provider_name=_provider_name(provider),
            model=model or settings.banter.model,
            message="e4 just hit the board and your whole opening prep is sweating.",
        ),
    )

    payload = service.move_banter(
        game_id=1,
        color="white",
        speaker="Qwen Hero",
        opponent="Qwen Villain",
        move="e4",
        fen="startpos",
    )

    assert payload is not None
    assert payload["source"] == "model"
    assert payload["provider"] == "ollama"
    assert payload["model"] == "qwen3:14b"
    assert payload["message"].startswith("e4 just hit")
    assert payload["move"] == "e4"
    assert payload["category"] == "banter"


def test_banter_service_falls_back_when_provider_cannot_support_role() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_BANTER_PROVIDER": "stockfish",
            "LEXICHESS_BANTER_MODEL": "stockfish_club",
        },
        dotenv_path=None,
    )

    service = build_banter_service(
        settings,
        provider_builder=lambda provider, settings, *, model=None: FakeBanterProvider(
            provider_name=_provider_name(provider),
            model=model or settings.banter.model,
            supports_system_instructions=False,
        ),
    )

    payload = service.move_banter(
        game_id=1,
        color="black",
        speaker="Trash Engine",
        opponent="Human Hope",
        move="...e5",
        fen="startpos",
    )

    assert payload is not None
    assert payload["source"] == "fallback"
    assert payload["provider"] == "deterministic"
    assert payload["move"] == "...e5"


def test_provider_backed_banter_service_can_suppress_output_without_fallback() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_BANTER_ENABLED": "true",
            "LEXICHESS_BANTER_ALLOW_FALLBACK": "false",
        },
        dotenv_path=None,
    )

    service = build_banter_service(
        settings,
        provider_builder=lambda provider, settings, *, model=None: FakeBanterProvider(
            provider_name=_provider_name(provider),
            model=model or settings.banter.model,
            supports_system_instructions=False,
        ),
    )

    payload = service.move_banter(
        game_id=1,
        color="white",
        speaker="Quiet Bot",
        opponent="Loud Bot",
        move="d4",
        fen="startpos",
    )

    assert payload is None


def test_deterministic_banter_finish_returns_none_for_draw() -> None:
    service = DeterministicBanterService()

    payload = service.finish(
        game_id=1,
        winner=None,
        loser=None,
        result="1/2-1/2",
        termination_reason="stalemate",
        fen="startpos",
    )

    assert payload is None
