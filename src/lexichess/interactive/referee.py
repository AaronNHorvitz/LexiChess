from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from lexichess.config import AppSettings
from lexichess.interactive.transcripts import (
    build_referee_finish,
    build_referee_provider_error,
    build_referee_ruling,
)
from lexichess.llm import MoveProvider, MoveRequest, ProviderError, build_provider
from lexichess.tournament.prompts import PromptTemplate

ProviderBuilder = Callable[..., MoveProvider]

REFEREE_RULING_PROMPT_VERSION = "referee_ruling.v1"
REFEREE_SYSTEM_PROMPT_VERSION = "referee_system.v1"
REFEREE_FINISH_PROMPT_VERSION = "referee_finish.v1"


class RefereeService(Protocol):
    def ruling(
        self,
        *,
        game_id: int,
        color: str,
        reason: str,
        detail: str,
        move_text: str | None,
        fen: str,
        legal_moves: tuple[str, ...],
    ) -> dict[str, Any]:
        ...

    def provider_error(
        self,
        *,
        game_id: int,
        color: str,
        detail: str,
        fen: str,
    ) -> dict[str, Any]:
        ...

    def finish(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None,
        fen: str,
    ) -> dict[str, Any]:
        ...


class DeterministicRefereeService:
    def __init__(self, *, speaker_name: str = "Gemma 4 Referee") -> None:
        self.speaker_name = speaker_name

    def ruling(
        self,
        *,
        game_id: int,
        color: str,
        reason: str,
        detail: str,
        move_text: str | None,
        fen: str,
        legal_moves: tuple[str, ...],
    ) -> dict[str, Any]:
        del game_id, fen, legal_moves
        payload = build_referee_ruling(
            color=color,
            reason=reason,
            detail=detail,
            move_text=move_text,
            speaker_name=self.speaker_name,
        )
        payload["source"] = "fallback"
        payload["provider"] = "deterministic"
        payload["model"] = "rules_engine"
        return payload

    def provider_error(
        self,
        *,
        game_id: int,
        color: str,
        detail: str,
        fen: str,
    ) -> dict[str, Any]:
        del game_id, fen
        payload = build_referee_provider_error(
            color=color,
            detail=detail,
            speaker_name=self.speaker_name,
        )
        payload["source"] = "fallback"
        payload["provider"] = "deterministic"
        payload["model"] = "rules_engine"
        return payload

    def finish(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None,
        fen: str,
    ) -> dict[str, Any]:
        del game_id, fen
        payload = build_referee_finish(
            result=result,
            termination_reason=termination_reason,
            speaker_name=self.speaker_name,
        )
        payload["source"] = "fallback"
        payload["provider"] = "deterministic"
        payload["model"] = "rules_engine"
        return payload


class ProviderBackedRefereeService:
    def __init__(
        self,
        settings: AppSettings,
        *,
        provider_builder: ProviderBuilder | None = None,
        fallback: RefereeService | None = None,
    ) -> None:
        self.settings = settings
        self.provider_builder = provider_builder or build_provider
        self.fallback = fallback or DeterministicRefereeService(
            speaker_name=settings.referee.speaker_name
        )
        self._provider: MoveProvider | None = None
        self._provider_initialized = False

    def ruling(
        self,
        *,
        game_id: int,
        color: str,
        reason: str,
        detail: str,
        move_text: str | None,
        fen: str,
        legal_moves: tuple[str, ...],
    ) -> dict[str, Any]:
        prompt = _build_referee_ruling_prompt(
            speaker_name=self.settings.referee.speaker_name,
            color=color,
            reason=reason,
            detail=detail,
            move_text=move_text,
            legal_moves=legal_moves,
        )
        payload = self._generate_payload(
            game_id=game_id,
            color=color,
            fen=fen,
            prompt=prompt,
            category="ruling",
        )
        if payload is not None:
            payload["reason"] = reason
            payload["detail"] = detail
            payload["coaching_suggestion"] = "Submit one legal SAN move."
            return payload
        if not self.settings.referee.allow_fallback:
            return _unavailable_referee_payload(
                speaker_name=self.settings.referee.speaker_name,
                category="ruling",
                message="Referee model unavailable. Rule engine ruling stands.",
                reason=reason,
                detail=detail,
            )
        return self.fallback.ruling(
            game_id=game_id,
            color=color,
            reason=reason,
            detail=detail,
            move_text=move_text,
            fen=fen,
            legal_moves=legal_moves,
        )

    def provider_error(
        self,
        *,
        game_id: int,
        color: str,
        detail: str,
        fen: str,
    ) -> dict[str, Any]:
        prompt = _build_referee_provider_error_prompt(
            speaker_name=self.settings.referee.speaker_name,
            color=color,
            detail=detail,
        )
        payload = self._generate_payload(
            game_id=game_id,
            color=color,
            fen=fen,
            prompt=prompt,
            category="system",
        )
        if payload is not None:
            payload["reason"] = "provider_error"
            payload["detail"] = detail
            return payload
        if not self.settings.referee.allow_fallback:
            return _unavailable_referee_payload(
                speaker_name=self.settings.referee.speaker_name,
                category="system",
                message="Referee model unavailable during a backend failure review.",
                reason="provider_error",
                detail=detail,
            )
        return self.fallback.provider_error(
            game_id=game_id,
            color=color,
            detail=detail,
            fen=fen,
        )

    def finish(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None,
        fen: str,
    ) -> dict[str, Any]:
        prompt = _build_referee_finish_prompt(
            speaker_name=self.settings.referee.speaker_name,
            result=result,
            termination_reason=termination_reason,
        )
        payload = self._generate_payload(
            game_id=game_id,
            color="white",
            fen=fen,
            prompt=prompt,
            category="finish",
        )
        if payload is not None:
            payload["result"] = result
            payload["termination_reason"] = termination_reason or "game_over"
            return payload
        if not self.settings.referee.allow_fallback:
            return _unavailable_referee_payload(
                speaker_name=self.settings.referee.speaker_name,
                category="finish",
                message="Referee model unavailable for the closing call.",
                result=result,
                termination_reason=termination_reason or "game_over",
            )
        return self.fallback.finish(
            game_id=game_id,
            result=result,
            termination_reason=termination_reason,
            fen=fen,
        )

    def _generate_payload(
        self,
        *,
        game_id: int,
        color: str,
        fen: str,
        prompt: PromptTemplate,
        category: str,
    ) -> dict[str, Any] | None:
        provider = self._resolve_provider()
        if provider is None:
            return None
        try:
            response = provider.request_move(
                MoveRequest(
                    game_id=game_id,
                    move_number=0,
                    color=color,
                    fen=fen,
                    prompt=prompt.prompt,
                    instructions=prompt.instructions,
                    legal_moves=(),
                    prompt_kind=prompt.kind,
                    prompt_version=prompt.version,
                    temperature=self.settings.referee.temperature,
                    max_output_tokens=self.settings.referee.max_output_tokens,
                )
            )
        except ProviderError:
            return None

        message = response.output_text.strip()
        if not message:
            return None
        return {
            "role": "referee",
            "speaker": self.settings.referee.speaker_name,
            "category": category,
            "message": message,
            "source": "model",
            "provider": response.provider,
            "model": response.model,
            "prompt_kind": prompt.kind,
            "prompt_version": prompt.version,
        }

    def _resolve_provider(self) -> MoveProvider | None:
        if not self.settings.referee.enabled:
            return None
        if self._provider_initialized:
            return self._provider

        self._provider_initialized = True
        try:
            provider = self.provider_builder(
                self.settings.referee.provider,
                self.settings,
                model=self.settings.referee.model,
            )
        except Exception:
            self._provider = None
            return None

        capabilities = provider.capabilities()
        if not capabilities.supports_system_instructions:
            self._provider = None
            return None

        self._provider = provider
        return provider


def build_referee_service(
    settings: AppSettings,
    *,
    provider_builder: ProviderBuilder | None = None,
) -> RefereeService:
    fallback = DeterministicRefereeService(
        speaker_name=settings.referee.speaker_name
    )
    if not settings.referee.enabled:
        return fallback
    return ProviderBackedRefereeService(
        settings,
        provider_builder=provider_builder,
        fallback=fallback,
    )


def _build_referee_ruling_prompt(
    *,
    speaker_name: str,
    color: str,
    reason: str,
    detail: str,
    move_text: str | None,
    legal_moves: tuple[str, ...],
) -> PromptTemplate:
    move_text_block = f"Rejected move text: {move_text!r}\n" if move_text else ""
    legal_moves_block = ", ".join(legal_moves[:12]) if legal_moves else "unknown"
    return PromptTemplate(
        kind="referee_ruling",
        version=REFEREE_RULING_PROMPT_VERSION,
        instructions=(
            f"You are {speaker_name}, the rational adult in the room for a live AI chess showmatch. "
            "Write one or two short sentences. Be grounded, witty, and clear. Explain the rule issue, "
            "do not choose a specific move, and end with a brief coaching nudge."
        ),
        prompt=(
            f"Color to move: {color}\n"
            f"Reason code: {reason}\n"
            f"Deterministic explanation: {detail}\n"
            f"{move_text_block}"
            f"Legal SAN examples: {legal_moves_block}"
        ),
    )


def _build_referee_provider_error_prompt(
    *,
    speaker_name: str,
    color: str,
    detail: str,
) -> PromptTemplate:
    return PromptTemplate(
        kind="referee_provider_error",
        version=REFEREE_SYSTEM_PROMPT_VERSION,
        instructions=(
            f"You are {speaker_name}. Write one or two short sentences explaining that the player backend failed, "
            "keeping the tone grounded and broadcast-friendly."
        ),
        prompt=(
            f"Color affected: {color}\n"
            f"System detail: {detail}\n"
            "The legality engine remains authoritative."
        ),
    )


def _build_referee_finish_prompt(
    *,
    speaker_name: str,
    result: str | None,
    termination_reason: str | None,
) -> PromptTemplate:
    return PromptTemplate(
        kind="referee_finish",
        version=REFEREE_FINISH_PROMPT_VERSION,
        instructions=(
            f"You are {speaker_name}. Write one or two short end-of-game broadcast sentences. "
            "If the ending is checkmate, you may shout GOOOOOAAAAAAALL and CHECKMATE."
        ),
        prompt=(
            f"Final result: {result or '*'}\n"
            f"Termination reason: {termination_reason or 'game_over'}"
        ),
    )


def _unavailable_referee_payload(
    *,
    speaker_name: str,
    category: str,
    message: str,
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "role": "referee",
        "speaker": speaker_name,
        "category": category,
        "message": message,
        "source": "unavailable",
        "provider": None,
        "model": None,
    }
    payload.update(extra)
    return payload
