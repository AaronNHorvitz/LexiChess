from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from lexichess.config import AppSettings
from lexichess.interactive.transcripts import (
    build_showmatch_finish,
    build_showmatch_hype,
    build_showmatch_intro,
    build_showmatch_illegal_move_callout,
    build_showmatch_postgame_interview,
    build_showmatch_quote_pin,
    build_showmatch_rivalry_recap,
)
from lexichess.llm import MoveProvider, MoveRequest, ProviderError, build_provider
from lexichess.tournament.prompts import PromptTemplate

ProviderBuilder = Callable[..., MoveProvider]

SHOWMATCH_PREGAME_PROMPT_VERSION = "showmatch_pregame.v1"
SHOWMATCH_HYPE_PROMPT_VERSION = "showmatch_hype.v1"
SHOWMATCH_FINISH_PROMPT_VERSION = "showmatch_finish.v1"
SHOWMATCH_ILLEGAL_PROMPT_VERSION = "showmatch_illegal_move.v1"
SHOWMATCH_INTERVIEW_PROMPT_VERSION = "showmatch_postgame_interview.v1"
SHOWMATCH_RIVALRY_PROMPT_VERSION = "showmatch_rivalry_recap.v1"
SHOWMATCH_QUOTE_PIN_PROMPT_VERSION = "showmatch_quote_pin.v1"


@dataclass(frozen=True, slots=True)
class QuoteCandidate:
    speaker: str
    message: str
    source_category: str
    event_id: int | None = None


class ShowmatchScriptService(Protocol):
    def pregame_intro(
        self,
        *,
        game_id: int,
        white_player: str,
        black_player: str,
    ) -> dict[str, Any] | None: ...

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
    ) -> dict[str, Any] | None: ...

    def finish(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None,
        winner: str | None,
        loser: str | None,
        fen: str,
    ) -> dict[str, Any] | None: ...

    def illegal_move_callout(
        self,
        *,
        game_id: int,
        color: str,
        player: str,
        move_text: str | None,
        reason: str,
        detail: str,
        fen: str,
    ) -> dict[str, Any] | None: ...

    def postgame_interviews(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None,
        winner: str | None,
        loser: str | None,
        fen: str,
    ) -> list[dict[str, Any]]: ...

    def rivalry_recap(
        self,
        *,
        game_id: int,
        white_player: str,
        black_player: str,
        result: str | None,
        banter_count: int,
        illegal_move_count: int,
        fen: str,
    ) -> dict[str, Any] | None: ...

    def quote_pins(
        self,
        *,
        game_id: int,
        quotes: tuple[QuoteCandidate, ...],
        fen: str,
    ) -> list[dict[str, Any]]: ...


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

    def illegal_move_callout(
        self,
        *,
        game_id: int,
        color: str,
        player: str,
        move_text: str | None,
        reason: str,
        detail: str,
        fen: str,
    ) -> dict[str, Any]:
        del game_id, fen
        payload = build_showmatch_illegal_move_callout(
            speaker_name=self.speaker_name,
            color=color,
            speaker=player,
            move_text=move_text,
            reason=reason,
            detail=detail,
        )
        payload["source"] = "fallback"
        payload["provider"] = "deterministic"
        payload["model"] = "showmatch_templates"
        return payload

    def postgame_interviews(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None,
        winner: str | None,
        loser: str | None,
        fen: str,
    ) -> list[dict[str, Any]]:
        del game_id, fen
        interviews: list[dict[str, Any]] = []
        if winner is not None:
            winner_payload = build_showmatch_postgame_interview(
                interviewer_name=self.speaker_name,
                player=winner,
                stance="winner",
                result=result,
                termination_reason=termination_reason,
            )
            winner_payload["source"] = "fallback"
            winner_payload["provider"] = "deterministic"
            winner_payload["model"] = "showmatch_templates"
            interviews.append(winner_payload)
        if loser is not None:
            loser_payload = build_showmatch_postgame_interview(
                interviewer_name=self.speaker_name,
                player=loser,
                stance="loser" if winner is not None else "draw",
                result=result,
                termination_reason=termination_reason,
            )
            loser_payload["source"] = "fallback"
            loser_payload["provider"] = "deterministic"
            loser_payload["model"] = "showmatch_templates"
            interviews.append(loser_payload)
        if winner is None and loser is None:
            draw_payload = build_showmatch_postgame_interview(
                interviewer_name=self.speaker_name,
                player="Both sides",
                stance="draw",
                result=result,
                termination_reason=termination_reason,
            )
            draw_payload["source"] = "fallback"
            draw_payload["provider"] = "deterministic"
            draw_payload["model"] = "showmatch_templates"
            interviews.append(draw_payload)
        return interviews

    def rivalry_recap(
        self,
        *,
        game_id: int,
        white_player: str,
        black_player: str,
        result: str | None,
        banter_count: int,
        illegal_move_count: int,
        fen: str,
    ) -> dict[str, Any]:
        del game_id, fen
        payload = build_showmatch_rivalry_recap(
            speaker_name=self.speaker_name,
            white_player=white_player,
            black_player=black_player,
            result=result,
            banter_count=banter_count,
            illegal_move_count=illegal_move_count,
        )
        payload["source"] = "fallback"
        payload["provider"] = "deterministic"
        payload["model"] = "showmatch_templates"
        return payload

    def quote_pins(
        self,
        *,
        game_id: int,
        quotes: tuple[QuoteCandidate, ...],
        fen: str,
    ) -> list[dict[str, Any]]:
        del game_id, fen
        payloads: list[dict[str, Any]] = []
        for rank, quote in enumerate(quotes, start=1):
            payload = build_showmatch_quote_pin(
                speaker_name=self.speaker_name,
                quoted_speaker=quote.speaker,
                quoted_message=quote.message,
                rank=rank,
                source_category=quote.source_category,
            )
            payload["source"] = "fallback"
            payload["provider"] = "deterministic"
            payload["model"] = "showmatch_templates"
            payload["event_id"] = quote.event_id
            payloads.append(payload)
        return payloads


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

    def illegal_move_callout(
        self,
        *,
        game_id: int,
        color: str,
        player: str,
        move_text: str | None,
        reason: str,
        detail: str,
        fen: str,
    ) -> dict[str, Any] | None:
        prompt = _build_showmatch_illegal_prompt(
            speaker_name=self.settings.showmatch_scripts.speaker_name,
            color=color,
            player=player,
            move_text=move_text,
            reason=reason,
            detail=detail,
        )
        payload = self._generate_payload(
            game_id=game_id,
            color=color,
            prompt=prompt,
            fen=fen,
            category="illegal_move_callout",
        )
        if payload is not None:
            payload["player"] = player
            payload["reason"] = reason
            payload["detail"] = detail
            payload["move_text"] = move_text
            return payload
        if not self.settings.showmatch_scripts.allow_fallback:
            return None
        return self.fallback.illegal_move_callout(
            game_id=game_id,
            color=color,
            player=player,
            move_text=move_text,
            reason=reason,
            detail=detail,
            fen=fen,
        )

    def postgame_interviews(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None,
        winner: str | None,
        loser: str | None,
        fen: str,
    ) -> list[dict[str, Any]]:
        interview_specs = _interview_specs(winner=winner, loser=loser)
        payloads: list[dict[str, Any]] = []
        for player, stance in interview_specs:
            prompt = _build_showmatch_interview_prompt(
                interviewer_name=self.settings.showmatch_scripts.speaker_name,
                player=player,
                stance=stance,
                result=result,
                termination_reason=termination_reason,
            )
            payload = self._generate_payload(
                game_id=game_id,
                color="white",
                prompt=prompt,
                fen=fen,
                category="postgame_interview",
            )
            if payload is not None:
                payload["speaker"] = player
                payload["interviewer"] = self.settings.showmatch_scripts.speaker_name
                payload["stance"] = stance
                payload["result"] = result
                payload["termination_reason"] = termination_reason or "game_over"
                payloads.append(payload)
        if payloads:
            return payloads
        if not self.settings.showmatch_scripts.allow_fallback:
            return []
        return self.fallback.postgame_interviews(
            game_id=game_id,
            result=result,
            termination_reason=termination_reason,
            winner=winner,
            loser=loser,
            fen=fen,
        )

    def rivalry_recap(
        self,
        *,
        game_id: int,
        white_player: str,
        black_player: str,
        result: str | None,
        banter_count: int,
        illegal_move_count: int,
        fen: str,
    ) -> dict[str, Any] | None:
        prompt = _build_showmatch_rivalry_prompt(
            speaker_name=self.settings.showmatch_scripts.speaker_name,
            white_player=white_player,
            black_player=black_player,
            result=result,
            banter_count=banter_count,
            illegal_move_count=illegal_move_count,
        )
        payload = self._generate_payload(
            game_id=game_id,
            color="white",
            prompt=prompt,
            fen=fen,
            category="rivalry_recap",
        )
        if payload is not None:
            payload["white_player"] = white_player
            payload["black_player"] = black_player
            payload["result"] = result
            payload["banter_count"] = banter_count
            payload["illegal_move_count"] = illegal_move_count
            return payload
        if not self.settings.showmatch_scripts.allow_fallback:
            return None
        return self.fallback.rivalry_recap(
            game_id=game_id,
            white_player=white_player,
            black_player=black_player,
            result=result,
            banter_count=banter_count,
            illegal_move_count=illegal_move_count,
            fen=fen,
        )

    def quote_pins(
        self,
        *,
        game_id: int,
        quotes: tuple[QuoteCandidate, ...],
        fen: str,
    ) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for rank, quote in enumerate(quotes, start=1):
            prompt = _build_showmatch_quote_pin_prompt(
                speaker_name=self.settings.showmatch_scripts.speaker_name,
                quoted_speaker=quote.speaker,
                quoted_message=quote.message,
                rank=rank,
                source_category=quote.source_category,
            )
            payload = self._generate_payload(
                game_id=game_id,
                color="white",
                prompt=prompt,
                fen=fen,
                category="quote_pin",
            )
            if payload is not None:
                payload["quoted_speaker"] = quote.speaker
                payload["quoted_message"] = quote.message
                payload["rank"] = rank
                payload["source_category"] = quote.source_category
                payload["event_id"] = quote.event_id
                payloads.append(payload)
        if payloads:
            return payloads
        if not self.settings.showmatch_scripts.allow_fallback:
            return []
        return self.fallback.quote_pins(
            game_id=game_id,
            quotes=quotes,
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


def _build_showmatch_illegal_prompt(
    *,
    speaker_name: str,
    color: str,
    player: str,
    move_text: str | None,
    reason: str,
    detail: str,
) -> PromptTemplate:
    return PromptTemplate(
        kind="showmatch_illegal_move_callout",
        version=SHOWMATCH_ILLEGAL_PROMPT_VERSION,
        instructions=(
            f"You are {speaker_name}, writing one or two short live-broadcast callout lines after a deterministic illegal chess move rejection. "
            "Be funny, sharp, and clear about the rule violation."
        ),
        prompt=(
            f"Color: {color}\n"
            f"Player: {player}\n"
            f"Rejected move text: {move_text or 'unknown'}\n"
            f"Reason: {reason}\n"
            f"Detail: {detail}"
        ),
    )


def _build_showmatch_interview_prompt(
    *,
    interviewer_name: str,
    player: str,
    stance: str,
    result: str | None,
    termination_reason: str | None,
) -> PromptTemplate:
    return PromptTemplate(
        kind="showmatch_postgame_interview",
        version=SHOWMATCH_INTERVIEW_PROMPT_VERSION,
        instructions=(
            f"You are ghostwriting one short post-game interview answer for {player}. "
            f"The interviewer is {interviewer_name}. Keep it funny, safe, and in first person."
        ),
        prompt=(
            f"Player: {player}\n"
            f"Stance: {stance}\n"
            f"Result: {result or '*'}\n"
            f"Termination reason: {termination_reason or 'game_over'}"
        ),
    )


def _build_showmatch_rivalry_prompt(
    *,
    speaker_name: str,
    white_player: str,
    black_player: str,
    result: str | None,
    banter_count: int,
    illegal_move_count: int,
) -> PromptTemplate:
    return PromptTemplate(
        kind="showmatch_rivalry_recap",
        version=SHOWMATCH_RIVALRY_PROMPT_VERSION,
        instructions=(
            f"You are {speaker_name}, writing one or two short rivalry-recap lines for the audience. "
            "Be witty and summary-driven."
        ),
        prompt=(
            f"White player: {white_player}\n"
            f"Black player: {black_player}\n"
            f"Result: {result or '*'}\n"
            f"Banter moments: {banter_count}\n"
            f"Illegal move interventions: {illegal_move_count}"
        ),
    )


def _build_showmatch_quote_pin_prompt(
    *,
    speaker_name: str,
    quoted_speaker: str,
    quoted_message: str,
    rank: int,
    source_category: str,
) -> PromptTemplate:
    return PromptTemplate(
        kind="showmatch_quote_pin",
        version=SHOWMATCH_QUOTE_PIN_PROMPT_VERSION,
        instructions=(
            f"You are {speaker_name}, writing one short quote-pin line for the audience. "
            "Introduce the quote cleanly and keep the original quote intact."
        ),
        prompt=(
            f"Rank: {rank}\n"
            f"Quoted speaker: {quoted_speaker}\n"
            f"Quoted message: {quoted_message}\n"
            f"Source category: {source_category}"
        ),
    )


def _interview_specs(
    *,
    winner: str | None,
    loser: str | None,
) -> tuple[tuple[str, str], ...]:
    specs: list[tuple[str, str]] = []
    if winner is not None:
        specs.append((winner, "winner"))
    if loser is not None:
        specs.append((loser, "loser"))
    if not specs:
        specs.append(("Both sides", "draw"))
    return tuple(specs)
