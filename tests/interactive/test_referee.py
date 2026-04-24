from __future__ import annotations

from lexichess.config import AppSettings
from lexichess.interactive.referee import (
    DeterministicRefereeService,
    ProviderBackedRefereeService,
    build_referee_service,
)
from lexichess.llm.base import MoveProvider, ProviderCapabilities, ProviderHealthReport
from lexichess.llm.types import MoveRequest, ProviderResponse


class FakeRefereeProvider(MoveProvider):
    def __init__(
        self,
        *,
        provider_name: str = "ollama",
        model: str = "gemma4:latest",
        message: str = "That move is illegal. Clean it up and submit one legal SAN move.",
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


def test_provider_backed_referee_service_uses_model_output() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_REFEREE_PROVIDER": "ollama",
            "LEXICHESS_REFEREE_MODEL": "gemma4:latest",
            "LEXICHESS_REFEREE_SPEAKER_NAME": "Gemma 4 Referee",
        },
        dotenv_path=None,
    )

    service = ProviderBackedRefereeService(
        settings,
        provider_builder=lambda provider, settings, *, model=None: FakeRefereeProvider(
            provider_name=_provider_name(provider),
            model=model or settings.referee.model,
            message="Absolutely not. That move is illegal, so settle down and try again.",
        ),
    )

    payload = service.ruling(
        game_id=1,
        color="white",
        reason="no_candidate_found",
        detail="No recognizable SAN or UCI move was found.",
        move_text="banana",
        fen="startpos",
        legal_moves=("e4", "d4"),
    )

    assert payload["source"] == "model"
    assert payload["provider"] == "ollama"
    assert payload["model"] == "gemma4:latest"
    assert payload["message"].startswith("Absolutely not.")
    assert payload["coaching_suggestion"] == "Submit one legal SAN move."


def test_referee_service_falls_back_when_provider_cannot_support_role() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_REFEREE_PROVIDER": "stockfish",
            "LEXICHESS_REFEREE_MODEL": "stockfish_club",
        },
        dotenv_path=None,
    )

    service = build_referee_service(
        settings,
        provider_builder=lambda provider, settings, *, model=None: FakeRefereeProvider(
            provider_name=_provider_name(provider),
            model=model or settings.referee.model,
            supports_system_instructions=False,
        ),
    )

    payload = service.finish(
        game_id=1,
        result="1-0",
        termination_reason="checkmate",
        fen="startpos",
    )

    assert payload["source"] == "fallback"
    assert payload["provider"] == "deterministic"
    assert "CHECKMATE" in payload["message"]


def test_deterministic_referee_service_sets_payload_contract() -> None:
    service = DeterministicRefereeService(speaker_name="Gemma 4 Ref")

    payload = service.ruling(
        game_id=1,
        color="black",
        reason="illegal_move",
        detail="'Qh9' is not a legal move.",
        move_text="Qh9",
        fen="startpos",
        legal_moves=("e5", "c5"),
    )

    assert payload["speaker"] == "Gemma 4 Ref"
    assert payload["category"] == "ruling"
    assert payload["reason"] == "illegal_move"
    assert payload["detail"] == "'Qh9' is not a legal move."
    assert payload["coaching_suggestion"] == "Reset, breathe, and submit one legal SAN move."
