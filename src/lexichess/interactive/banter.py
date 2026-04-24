from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from lexichess.config import AppSettings
from lexichess.interactive.transcripts import build_finish_banter, build_player_banter
from lexichess.llm import MoveProvider, MoveRequest, ProviderError, build_provider
from lexichess.tournament.prompts import PromptTemplate

ProviderBuilder = Callable[..., MoveProvider]

PLAYER_BANTER_PROMPT_VERSION = "player_banter.v1"
PLAYER_FINISH_BANTER_PROMPT_VERSION = "player_finish_banter.v1"


class BanterService(Protocol):
    def move_banter(
        self,
        *,
        game_id: int,
        color: str,
        speaker: str,
        opponent: str | None,
        move: str,
        fen: str,
    ) -> dict[str, Any] | None: ...

    def finish(
        self,
        *,
        game_id: int,
        winner: str | None,
        loser: str | None,
        result: str | None,
        termination_reason: str | None,
        fen: str,
    ) -> dict[str, Any] | None: ...


class DeterministicBanterService:
    def move_banter(
        self,
        *,
        game_id: int,
        color: str,
        speaker: str,
        opponent: str | None,
        move: str,
        fen: str,
    ) -> dict[str, Any]:
        del game_id, fen, opponent
        payload = build_player_banter(
            color=color,
            speaker=speaker,
            move=move,
        )
        payload["source"] = "fallback"
        payload["provider"] = "deterministic"
        payload["model"] = "trash_talk_templates"
        return payload

    def finish(
        self,
        *,
        game_id: int,
        winner: str | None,
        loser: str | None,
        result: str | None,
        termination_reason: str | None,
        fen: str,
    ) -> dict[str, Any] | None:
        del game_id, fen, loser, termination_reason
        payload = build_finish_banter(winner=winner, result=result)
        if payload is None:
            return None
        payload["source"] = "fallback"
        payload["provider"] = "deterministic"
        payload["model"] = "trash_talk_templates"
        return payload


class ProviderBackedBanterService:
    def __init__(
        self,
        settings: AppSettings,
        *,
        provider_builder: ProviderBuilder | None = None,
        fallback: BanterService | None = None,
    ) -> None:
        self.settings = settings
        self.provider_builder = provider_builder or build_provider
        self.fallback = fallback or DeterministicBanterService()
        self._provider: MoveProvider | None = None
        self._provider_initialized = False

    def move_banter(
        self,
        *,
        game_id: int,
        color: str,
        speaker: str,
        opponent: str | None,
        move: str,
        fen: str,
    ) -> dict[str, Any] | None:
        prompt = _build_move_banter_prompt(
            speaker=speaker,
            color=color,
            opponent=opponent,
            move=move,
            fen=fen,
        )
        payload = self._generate_payload(
            game_id=game_id,
            color=color,
            speaker=speaker,
            prompt=prompt,
            fen=fen,
            category="banter",
            target="opponent",
        )
        if payload is not None:
            payload["move"] = move
            payload["color"] = color
            if opponent is not None:
                payload["opponent"] = opponent
            return payload
        if not self.settings.banter.allow_fallback:
            return None
        return self.fallback.move_banter(
            game_id=game_id,
            color=color,
            speaker=speaker,
            opponent=opponent,
            move=move,
            fen=fen,
        )

    def finish(
        self,
        *,
        game_id: int,
        winner: str | None,
        loser: str | None,
        result: str | None,
        termination_reason: str | None,
        fen: str,
    ) -> dict[str, Any] | None:
        if winner is None or result in {None, "1/2-1/2"}:
            return self.fallback.finish(
                game_id=game_id,
                winner=winner,
                loser=loser,
                result=result,
                termination_reason=termination_reason,
                fen=fen,
            )

        assert result is not None
        prompt = _build_finish_banter_prompt(
            winner=winner,
            loser=loser,
            result=result,
            termination_reason=termination_reason,
            fen=fen,
        )
        payload = self._generate_payload(
            game_id=game_id,
            color="white",
            speaker=winner,
            prompt=prompt,
            fen=fen,
            category="finish",
            target="crowd",
        )
        if payload is not None:
            payload["result"] = result
            payload["termination_reason"] = termination_reason or "game_over"
            if loser is not None:
                payload["opponent"] = loser
            return payload
        if not self.settings.banter.allow_fallback:
            return None
        return self.fallback.finish(
            game_id=game_id,
            winner=winner,
            loser=loser,
            result=result,
            termination_reason=termination_reason,
            fen=fen,
        )

    def _generate_payload(
        self,
        *,
        game_id: int,
        color: str,
        speaker: str,
        prompt: PromptTemplate,
        fen: str,
        category: str,
        target: str,
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
                    temperature=self.settings.banter.temperature,
                    max_output_tokens=self.settings.banter.max_output_tokens,
                )
            )
        except ProviderError:
            return None

        message = response.output_text.strip()
        if not message:
            return None

        return {
            "role": "player",
            "speaker": speaker,
            "category": category,
            "target": target,
            "message": message,
            "source": "model",
            "provider": response.provider,
            "model": response.model,
            "prompt_kind": prompt.kind,
            "prompt_version": prompt.version,
        }

    def _resolve_provider(self) -> MoveProvider | None:
        if not self.settings.banter.enabled:
            return None
        if self._provider_initialized:
            return self._provider

        self._provider_initialized = True
        try:
            provider = self.provider_builder(
                self.settings.banter.provider,
                self.settings,
                model=self.settings.banter.model,
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


def build_banter_service(
    settings: AppSettings,
    *,
    provider_builder: ProviderBuilder | None = None,
) -> BanterService:
    fallback = DeterministicBanterService()
    if not settings.banter.enabled:
        return fallback
    return ProviderBackedBanterService(
        settings,
        provider_builder=provider_builder,
        fallback=fallback,
    )


def _build_move_banter_prompt(
    *,
    speaker: str,
    color: str,
    opponent: str | None,
    move: str,
    fen: str,
) -> PromptTemplate:
    return PromptTemplate(
        kind="player_banter",
        version=PLAYER_BANTER_PROMPT_VERSION,
        instructions=(
            f"You are ghostwriting one short trash-talk line for {speaker} in a live AI chess showmatch. "
            "Be funny, cocky, and PG-13. Roast the opponent's chess, not their identity. "
            "Mention the move and keep it to one or two short sentences."
        ),
        prompt=(
            f"Speaker: {speaker}\n"
            f"Color: {color}\n"
            f"Opponent: {opponent or 'the other side'}\n"
            f"Move just played: {move}\n"
            f"Board FEN after move: {fen}\n"
            "Tone target: entertaining, sharp, arena-ready."
        ),
    )


def _build_finish_banter_prompt(
    *,
    winner: str,
    loser: str | None,
    result: str,
    termination_reason: str | None,
    fen: str,
) -> PromptTemplate:
    return PromptTemplate(
        kind="player_finish_banter",
        version=PLAYER_FINISH_BANTER_PROMPT_VERSION,
        instructions=(
            f"You are ghostwriting the post-game victory line for {winner} after a live AI chess showmatch. "
            "Be triumphant, funny, and safe. Keep it to one or two short sentences."
        ),
        prompt=(
            f"Winner: {winner}\n"
            f"Loser: {loser or 'the other side'}\n"
            f"Result: {result}\n"
            f"Termination reason: {termination_reason or 'game_over'}\n"
            f"Board FEN at finish: {fen}"
        ),
    )
