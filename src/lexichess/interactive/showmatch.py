from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from lexichess.config import AppSettings
from lexichess.interactive.transcripts import (
    build_showmatch_finish,
    build_showmatch_hype,
    build_showmatch_intro,
)
from lexichess.llm import MoveProvider, MoveRequest, ProviderError, build_provider
from lexichess.tournament.prompts import PromptTemplate

ProviderBuilder = Callable[..., MoveProvider]

SHOWMATCH_PREGAME_PROMPT_VERSION = "showmatch_pregame.v1"
SHOWMATCH_HYPE_PROMPT_VERSION = "showmatch_hype.v1"
SHOWMATCH_FINISH_PROMPT_VERSION = "showmatch_finish.v1"


class ShowmatchScriptService(Protocol):
    def pregame_intro(
        self,
        *,
        game_id: int,
        white_player: str,
        black_player: str,
    ) -> dict[str, Any] | None:
        ...

    def midgame_hype(
        self,
        *,
        game_id: int,
        color: str,
        speaker: str,
        opponent: str | None,
        move: str,
        ply: int,
        tags: tuple[str, ...],
        fen: str,
    ) -> dict[str, Any] | None:
        ...

    def finish(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None,
        winner: str | None,
        loser: str | None,
        fen: str,
    ) -> dict[str, Any] | None:
        ...


class DeterministicShowmatchScriptService:
    def __init__(self, *, speaker_name: str = "Arena Booth") -> None:
        self.speaker_name = speaker_name

    def pregame_intro(
        self,
        *,
        game_id: int,
        white_player: str,
        black_player: str,
    ) -> dict[str, Any]:
        del game_id
        payload = build_showmatch_intro(
            speaker_name=self.speaker_name,
            white_player=white_player,
            black_player=black_player,
        )
        payload["source"] = "fallback"
        payload["provider"] = "deterministic"
        payload["model"] = "showmatch_templates"
        return payload

    def midgame_hype(
        self,
        *,
        game_id: int,
        color: str,
        speaker: str,
        opponent: str | None,
        move: str,
        ply: int,
        tags: tuple[str, ...],
        fen: str,
    ) -> dict[str, Any]:
        del game_id, fen
        payload = build_showmatch_hype(
            speaker_name=self.speaker_name,
            color=color,
            speaker=speaker,
            opponent=opponent,
            move=move,
            ply=ply,
            tags=tags,
        )
        payload["source"] = "fallback"
        payload["provider"] = "deterministic"
        payload["model"] = "showmatch_templates"
        return payload

    def finish(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None,
        winner: str | None,
        loser: str | None,
        fen: str,
    ) -> dict[str, Any]:
        del game_id, fen
        payload = build_showmatch_finish(
            speaker_name=self.speaker_name,
            result=result,
            termination_reason=termination_reason,
            winner=winner,
            loser=loser,
        )
        payload["source"] = "fallback"
        payload["provider"] = "deterministic"
        payload["model"] = "showmatch_templates"
        return payload


class ProviderBackedShowmatchScriptService:
    def __init__(
        self,
        settings: AppSettings,
        *,
        provider_builder: ProviderBuilder | None = None,
        fallback: ShowmatchScriptService | None = None,
    ) -> None:
        self.settings = settings
        self.provider_builder = provider_builder or build_provider
        self.fallback = fallback or DeterministicShowmatchScriptService(
            speaker_name=settings.showmatch_scripts.speaker_name
        )
        self._provider: MoveProvider | None = None
        self._provider_initialized = False

    def pregame_intro(
        self,
        *,
        game_id: int,
        white_player: str,
        black_player: str,
    ) -> dict[str, Any] | None:
        prompt = _build_showmatch_pregame_prompt(
            speaker_name=self.settings.showmatch_scripts.speaker_name,
            white_player=white_player,
            black_player=black_player,
        )
        payload = self._generate_payload(
            game_id=game_id,
            color="white",
            prompt=prompt,
            fen="startpos",
            category="pregame",
        )
        if payload is not None:
            payload["white_player"] = white_player
            payload["black_player"] = black_player
            return payload
        if not self.settings.showmatch_scripts.allow_fallback:
            return None
        return self.fallback.pregame_intro(
            game_id=game_id,
            white_player=white_player,
            black_player=black_player,
        )

    def midgame_hype(
        self,
        *,
        game_id: int,
        color: str,
        speaker: str,
        opponent: str | None,
        move: str,
        ply: int,
        tags: tuple[str, ...],
        fen: str,
    ) -> dict[str, Any] | None:
        prompt = _build_showmatch_hype_prompt(
            speaker_name=self.settings.showmatch_scripts.speaker_name,
            color=color,
            speaker=speaker,
            opponent=opponent,
            move=move,
            ply=ply,
            tags=tags,
            fen=fen,
        )
        payload = self._generate_payload(
            game_id=game_id,
            color=color,
            prompt=prompt,
            fen=fen,
            category="hype",
        )
        if payload is not None:
            payload["color"] = color
            payload["player"] = speaker
            payload["opponent"] = opponent
            payload["move"] = move
            payload["ply"] = ply
            payload["tags"] = list(tags)
            return payload
        if not self.settings.showmatch_scripts.allow_fallback:
            return None
        return self.fallback.midgame_hype(
            game_id=game_id,
            color=color,
            speaker=speaker,
            opponent=opponent,
            move=move,
            ply=ply,
            tags=tags,
            fen=fen,
        )

    def finish(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None,
        winner: str | None,
        loser: str | None,
        fen: str,
    ) -> dict[str, Any] | None:
        prompt = _build_showmatch_finish_prompt(
            speaker_name=self.settings.showmatch_scripts.speaker_name,
            result=result,
            termination_reason=termination_reason,
            winner=winner,
            loser=loser,
            fen=fen,
        )
        payload = self._generate_payload(
            game_id=game_id,
            color="white",
            prompt=prompt,
            fen=fen,
            category="finish",
        )
        if payload is not None:
            payload["result"] = result
            payload["termination_reason"] = termination_reason or "game_over"
            payload["winner"] = winner
            payload["loser"] = loser
            return payload
        if not self.settings.showmatch_scripts.allow_fallback:
            return None
        return self.fallback.finish(
            game_id=game_id,
            result=result,
            termination_reason=termination_reason,
            winner=winner,
            loser=loser,
            fen=fen,
        )

    def _generate_payload(
        self,
        *,
        game_id: int,
        color: str,
        prompt: PromptTemplate,
        fen: str,
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
                    temperature=self.settings.showmatch_scripts.temperature,
                    max_output_tokens=self.settings.showmatch_scripts.max_output_tokens,
                )
            )
        except ProviderError:
            return None

        message = response.output_text.strip()
        if not message:
            return None
        return {
            "role": "showmatch",
            "speaker": self.settings.showmatch_scripts.speaker_name,
            "category": category,
            "target": "crowd",
            "message": message,
            "source": "model",
            "provider": response.provider,
            "model": response.model,
            "prompt_kind": prompt.kind,
            "prompt_version": prompt.version,
        }

    def _resolve_provider(self) -> MoveProvider | None:
        if not self.settings.showmatch_scripts.enabled:
            return None
        if self._provider_initialized:
            return self._provider

        self._provider_initialized = True
        try:
            provider = self.provider_builder(
                self.settings.showmatch_scripts.provider,
                self.settings,
                model=self.settings.showmatch_scripts.model,
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


def build_showmatch_script_service(
    settings: AppSettings,
    *,
    provider_builder: ProviderBuilder | None = None,
) -> ShowmatchScriptService:
    fallback = DeterministicShowmatchScriptService(
        speaker_name=settings.showmatch_scripts.speaker_name
    )
    if not settings.showmatch_scripts.enabled:
        return fallback
    return ProviderBackedShowmatchScriptService(
        settings,
        provider_builder=provider_builder,
        fallback=fallback,
    )


def _build_showmatch_pregame_prompt(
    *,
    speaker_name: str,
    white_player: str,
    black_player: str,
) -> PromptTemplate:
    return PromptTemplate(
        kind="showmatch_pregame",
        version=SHOWMATCH_PREGAME_PROMPT_VERSION,
        instructions=(
            f"You are {speaker_name}, writing one or two short pregame lines for a comedic live AI chess showmatch. "
            "Be energetic, funny, and safe. Set the scene without insulting identity groups."
        ),
        prompt=(
            f"White player: {white_player}\n"
            f"Black player: {black_player}\n"
            "Audience expectation: witty chaos, legal moves, loud reactions."
        ),
    )


def _build_showmatch_hype_prompt(
    *,
    speaker_name: str,
    color: str,
    speaker: str,
    opponent: str | None,
    move: str,
    ply: int,
    tags: tuple[str, ...],
    fen: str,
) -> PromptTemplate:
    return PromptTemplate(
        kind="showmatch_hype",
        version=SHOWMATCH_HYPE_PROMPT_VERSION,
        instructions=(
            f"You are {speaker_name}, writing one or two short arena-hype lines for a live AI chess showmatch. "
            "Be punchy, funny, and crowd-friendly."
        ),
        prompt=(
            f"Color: {color}\n"
            f"Player: {speaker}\n"
            f"Opponent: {opponent or 'the other side'}\n"
            f"Move: {move}\n"
            f"Ply: {ply}\n"
            f"Tags: {', '.join(tags) if tags else 'none'}\n"
            f"Board FEN: {fen}"
        ),
    )


def _build_showmatch_finish_prompt(
    *,
    speaker_name: str,
    result: str | None,
    termination_reason: str | None,
    winner: str | None,
    loser: str | None,
    fen: str,
) -> PromptTemplate:
    return PromptTemplate(
        kind="showmatch_finish",
        version=SHOWMATCH_FINISH_PROMPT_VERSION,
        instructions=(
            f"You are {speaker_name}, writing one or two short post-game wrap-up lines for a live AI chess showmatch. "
            "Be funny and conclusive. Celebrate checkmate, or frame a draw as unresolved drama."
        ),
        prompt=(
            f"Result: {result or '*'}\n"
            f"Termination reason: {termination_reason or 'game_over'}\n"
            f"Winner: {winner or 'none'}\n"
            f"Loser: {loser or 'none'}\n"
            f"Board FEN at finish: {fen}"
        ),
    )
