from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from lexichess.chess import ChessBoard
from lexichess.config import AppSettings, SeatController
from lexichess.interactive.banter import BanterService, DeterministicBanterService
from lexichess.interactive.referee import (
    DeterministicRefereeService,
    RefereeService,
)
from lexichess.interactive.showmatch import (
    DeterministicShowmatchScriptService,
    QuoteCandidate,
    ShowmatchScriptService,
)
from lexichess.llm import MoveProvider, MoveRequest, ProviderError, build_provider
from lexichess.storage import SQLiteRepository
from lexichess.tournament.models import InvalidMoveNotification
from lexichess.tournament.prompts import (
    PromptTemplate,
    build_benchmark_move_prompt,
    build_invalid_move_retry_prompt,
)
from lexichess.tournament.replay import accepted_san_moves

ProviderBuilder = Callable[..., MoveProvider]


@dataclass(frozen=True, slots=True)
class LiveAdvanceResult:
    game_id: int
    status: str
    color: str | None = None
    move_san: str | None = None
    detail: str | None = None


@dataclass(slots=True)
class _LiveLoopHandle:
    game_id: int
    thread: threading.Thread
    stop_event: threading.Event
    started_at: float
    last_outcome: str | None = None
    last_error: str | None = None


class InteractiveGameRuntime:
    def __init__(
        self,
        repository: SQLiteRepository,
        settings: AppSettings,
        *,
        provider_builder: ProviderBuilder | None = None,
        referee_service: RefereeService | None = None,
        banter_service: BanterService | None = None,
        showmatch_script_service: ShowmatchScriptService | None = None,
        max_correction_attempts: int = 1,
    ) -> None:
        self.repository = repository
        self.settings = settings
        self.provider_builder = provider_builder or build_provider
        self.referee_service = referee_service or DeterministicRefereeService(
            speaker_name=settings.referee.speaker_name
        )
        self.banter_service = banter_service or DeterministicBanterService()
        self.showmatch_script_service = (
            showmatch_script_service
            or DeterministicShowmatchScriptService(
                speaker_name=settings.showmatch_scripts.speaker_name
            )
        )
        self.max_correction_attempts = max_correction_attempts

    def emit_pregame_intro(self, game_id: int) -> dict[str, Any] | None:
        game = self._require_game(game_id)
        if not self._showmatch_enabled(game):
            return None
        if self._showmatch_script_exists(game_id, category="pregame"):
            return None

        white_player = self._seat_speaker_name(game_id, "white")
        black_player = self._seat_speaker_name(game_id, "black")
        payload = self.showmatch_script_service.pregame_intro(
            game_id=game_id,
            white_player=white_player,
            black_player=black_player,
        )
        if payload is None:
            return None
        return self._emit_showmatch_script(game_id=game_id, color=None, payload=payload)

    def advance_once(self, game_id: int) -> LiveAdvanceResult:
        game = self._require_game(game_id)
        if str(game["status"]) == "completed":
            return LiveAdvanceResult(
                game_id=game_id,
                status="completed",
                detail=str(game.get("termination_reason") or "completed"),
            )

        board = self._board_for_game(game_id)
        if board.is_game_over():
            return self._finish_from_board(game_id, board)

        color = board.turn_color
        seat = self._seat_map(game_id)[color]
        self.repository.update_game_status(game_id, status="running")

        if seat["controller"] == SeatController.HUMAN.value:
            self._log_waiting_for_human(game_id, color=color, ply=board.ply, seat=seat)
            return LiveAdvanceResult(
                game_id=game_id,
                status="waiting_for_human",
                color=color,
                detail=f"Waiting for {color} human move.",
            )

        return self._run_model_turn(game_id, board, seat)

    def submit_human_move(
        self,
        game_id: int,
        *,
        color: str,
        move_text: str,
        actor_name: str | None = None,
    ) -> dict[str, Any]:
        normalized_color = color.strip().lower()
        if normalized_color not in {"white", "black"}:
            raise ValueError(f"Unsupported seat color: {color}")

        seat = self._seat_map(game_id)[normalized_color]
        if seat["controller"] != SeatController.HUMAN.value:
            raise ValueError(f"{normalized_color} seat is not human-controlled.")

        game = self._require_game(game_id)
        board = self._board_for_game(game_id)
        if board.turn_color != normalized_color:
            raise ValueError(f"It is not {normalized_color}'s turn.")

        fen_before = board.fen
        interpretation = board.parse_move_text(move_text)
        display_name = (
            actor_name
            or seat.get("display_name")
            or seat.get("claimed_by")
            or f"human:{normalized_color}"
        )

        if interpretation.san is None:
            deterministic_explanation = board.describe_interpretation_failure(
                interpretation
            )
            self.repository.log_turn(
                game_id=game_id,
                ply=board.ply,
                attempt=1,
                color=normalized_color,
                provider="human",
                model=str(display_name),
                prompt_kind="human_move",
                prompt_version="human_manual.v1",
                prompt="Human move submission",
                instructions="Submit one SAN move.",
                raw_response_text=move_text,
                raw_response_json=None,
                candidate_move=interpretation.candidate,
                parsed_move_san=None,
                parsed_move_uci=None,
                fen_before=fen_before,
                fen_after=None,
                is_legal=False,
                latency_ms=None,
                error=interpretation.reason,
                deterministic_explanation=deterministic_explanation,
            )
            event = self.repository.log_game_event(
                game_id=game_id,
                event_type="human_move_rejected",
                color=normalized_color,
                payload={
                    "color": normalized_color,
                    "move_text": move_text,
                    "reason": interpretation.reason or "invalid_or_illegal_move",
                    "detail": deterministic_explanation,
                },
            )
            self._emit_referee_message(
                game_id=game_id,
                color=normalized_color,
                payload=self.referee_service.ruling(
                    game_id=game_id,
                    color=normalized_color,
                    reason=interpretation.reason or "invalid_or_illegal_move",
                    detail=deterministic_explanation,
                    move_text=move_text,
                    fen=fen_before,
                    legal_moves=tuple(board.legal_moves_san()),
                ),
            )
            self._maybe_emit_showmatch_illegal_move_callout(
                game_id=game_id,
                color=normalized_color,
                player=str(display_name),
                move_text=move_text,
                reason=interpretation.reason or "invalid_or_illegal_move",
                detail=deterministic_explanation,
                fen=fen_before,
            )
            raise ValueError(str(event["payload_json"]["detail"]))

        normalized_move = board.apply_san(interpretation.san)
        turn_id = self.repository.log_turn(
            game_id=game_id,
            ply=board.ply - 1,
            attempt=1,
            color=normalized_color,
            provider="human",
            model=str(display_name),
            prompt_kind="human_move",
            prompt_version="human_manual.v1",
            prompt="Human move submission",
            instructions="Submit one SAN move.",
            raw_response_text=move_text,
            raw_response_json=None,
            candidate_move=interpretation.candidate,
            parsed_move_san=normalized_move,
            parsed_move_uci=interpretation.uci,
            fen_before=fen_before,
            fen_after=board.fen,
            is_legal=True,
            latency_ms=None,
            error=None,
        )
        self.repository.update_game_status(game_id, status="running")
        event = self.repository.log_game_event(
            game_id=game_id,
            event_type="human_move_submitted",
            color=normalized_color,
            payload={
                "color": normalized_color,
                "actor_name": display_name,
                "move": normalized_move,
                "turn_id": turn_id,
                "fen_after": board.fen,
            },
        )
        if board.is_game_over():
            self._finish_from_board(game_id, board)
        elif self._banter_enabled(game):
            banter_payload = self.banter_service.move_banter(
                game_id=game_id,
                color=normalized_color,
                speaker=str(display_name),
                opponent=self._seat_speaker_name(
                    game_id, self._opponent_color(normalized_color)
                ),
                move=normalized_move,
                fen=board.fen,
            )
            if banter_payload is not None:
                self._emit_player_banter(
                    game_id=game_id,
                    color=normalized_color,
                    payload=banter_payload,
                )
        self._maybe_emit_showmatch_hype(
            game_id=game_id,
            color=normalized_color,
            speaker=str(display_name),
            move=normalized_move,
            board=board,
        )
        return event

    def _run_model_turn(
        self,
        game_id: int,
        board: ChessBoard,
        seat: dict[str, Any],
    ) -> LiveAdvanceResult:
        color = board.turn_color
        fen_before = board.fen
        legal_moves = tuple(board.legal_moves_san())
        provider = self.provider_builder(
            str(seat["provider"]),
            self.settings,
            model=str(seat["model"]),
        )
        last_notification: InvalidMoveNotification | None = None
        referee_note: str | None = None

        for attempt in range(1, self.max_correction_attempts + 2):
            prompt_template = self._prompt_for_attempt(
                board=board,
                legal_moves=legal_moves,
                attempt=attempt,
                notification=last_notification,
                referee_note=referee_note,
            )
            prompt_kind, prompt_version = self._prompt_metadata(
                provider, prompt_template
            )
            request = MoveRequest(
                game_id=game_id,
                move_number=board.ply,
                color=color,
                fen=fen_before,
                prompt_kind=prompt_kind,
                prompt_version=prompt_version,
                prompt=prompt_template.prompt,
                instructions=prompt_template.instructions,
                legal_moves=legal_moves,
                temperature=self.settings.move_temperature,
                max_output_tokens=self.settings.max_output_tokens,
            )

            try:
                response = provider.request_move(request)
            except ProviderError as exc:
                self._log_provider_error(
                    game_id=game_id,
                    board=board,
                    seat=seat,
                    attempt=attempt,
                    prompt_template=prompt_template,
                    prompt_kind=prompt_kind,
                    prompt_version=prompt_version,
                    error=str(exc),
                )
                self._emit_referee_message(
                    game_id=game_id,
                    color=color,
                    payload=self.referee_service.provider_error(
                        game_id=game_id,
                        color=color,
                        detail=str(exc),
                        fen=board.fen,
                    ),
                )
                return self._finish_invalid_game(
                    game_id=game_id,
                    board=board,
                    color=color,
                    reason="provider_error",
                    detail=str(exc),
                )

            interpretation = board.parse_move_text(response.output_text)
            if interpretation.san is not None:
                normalized_move = board.apply_san(interpretation.san)
                turn_id = self.repository.log_turn(
                    game_id=game_id,
                    ply=request.move_number,
                    attempt=attempt,
                    color=color,
                    provider=provider.provider_name,
                    model=provider.model,
                    prompt_kind=prompt_kind,
                    prompt_version=prompt_version,
                    prompt=prompt_template.prompt,
                    instructions=prompt_template.instructions,
                    raw_response_text=response.output_text,
                    raw_response_json=(
                        response.raw_response
                        if self.settings.log_raw_response_json
                        else None
                    ),
                    candidate_move=interpretation.candidate,
                    parsed_move_san=normalized_move,
                    parsed_move_uci=interpretation.uci,
                    fen_before=fen_before,
                    fen_after=board.fen,
                    is_legal=True,
                    latency_ms=response.latency_ms,
                    error=None,
                    referee_note=referee_note,
                )
                self.repository.log_game_event(
                    game_id=game_id,
                    event_type="model_move_accepted",
                    color=color,
                    payload={
                        "color": color,
                        "controller": seat["controller"],
                        "provider": provider.provider_name,
                        "model": provider.model,
                        "move": normalized_move,
                        "turn_id": turn_id,
                        "ply": request.move_number,
                        "fen_after": board.fen,
                    },
                )
                if self._banter_enabled(self._require_game(game_id)):
                    banter_payload = self.banter_service.move_banter(
                        game_id=game_id,
                        color=color,
                        speaker=str(
                            seat.get("display_name")
                            or f"{provider.provider_name}:{provider.model}"
                        ),
                        opponent=self._seat_speaker_name(
                            game_id, self._opponent_color(color)
                        ),
                        move=normalized_move,
                        fen=board.fen,
                    )
                    if banter_payload is not None:
                        self._emit_player_banter(
                            game_id=game_id,
                            color=color,
                            payload=banter_payload,
                        )
                self._maybe_emit_showmatch_hype(
                    game_id=game_id,
                    color=color,
                    speaker=str(
                        seat.get("display_name")
                        or f"{provider.provider_name}:{provider.model}"
                    ),
                    move=normalized_move,
                    board=board,
                )
                if board.is_game_over():
                    return self._finish_from_board(game_id, board)
                return LiveAdvanceResult(
                    game_id=game_id,
                    status="move_applied",
                    color=color,
                    move_san=normalized_move,
                )

            deterministic_explanation = board.describe_interpretation_failure(
                interpretation
            )
            referee_note = deterministic_explanation
            last_notification = InvalidMoveNotification(
                game_id=game_id,
                ply=board.ply,
                attempt=attempt,
                color=color,
                provider=provider.provider_name,
                model=provider.model,
                fen=fen_before,
                raw_response_text=response.output_text,
                candidate_move=interpretation.candidate,
                reason=interpretation.reason or "invalid_or_illegal_move",
                deterministic_explanation=deterministic_explanation,
                legal_moves=legal_moves,
                prompt_kind=prompt_kind,
                prompt_version=prompt_version,
            )

            turn_id = self.repository.log_turn(
                game_id=game_id,
                ply=request.move_number,
                attempt=attempt,
                color=color,
                provider=provider.provider_name,
                model=provider.model,
                prompt_kind=prompt_kind,
                prompt_version=prompt_version,
                prompt=prompt_template.prompt,
                instructions=prompt_template.instructions,
                raw_response_text=response.output_text,
                raw_response_json=(
                    response.raw_response
                    if self.settings.log_raw_response_json
                    else None
                ),
                candidate_move=interpretation.candidate,
                parsed_move_san=None,
                parsed_move_uci=None,
                fen_before=fen_before,
                fen_after=None,
                is_legal=False,
                latency_ms=response.latency_ms,
                error=interpretation.reason,
                deterministic_explanation=deterministic_explanation,
                referee_note=referee_note,
            )
            self.repository.log_hallucination(
                game_id=game_id,
                turn_id=turn_id,
                color=color,
                provider=provider.provider_name,
                model=provider.model,
                raw_response_text=response.output_text,
                candidate_move=interpretation.candidate,
                reason=interpretation.reason or "invalid_or_illegal_move",
                details=deterministic_explanation,
            )
            self.repository.log_game_event(
                game_id=game_id,
                event_type="model_move_rejected",
                color=color,
                payload={
                    "color": color,
                    "provider": provider.provider_name,
                    "model": provider.model,
                    "attempt": attempt,
                    "reason": interpretation.reason or "invalid_or_illegal_move",
                    "detail": deterministic_explanation,
                    "raw_response_text": response.output_text,
                },
            )
            self._emit_referee_message(
                game_id=game_id,
                color=color,
                payload=self.referee_service.ruling(
                    game_id=game_id,
                    color=color,
                    reason=interpretation.reason or "invalid_or_illegal_move",
                    detail=deterministic_explanation,
                    move_text=response.output_text,
                    fen=fen_before,
                    legal_moves=legal_moves,
                ),
            )
            self._maybe_emit_showmatch_illegal_move_callout(
                game_id=game_id,
                color=color,
                player=str(
                    seat.get("display_name")
                    or f"{provider.provider_name}:{provider.model}"
                ),
                move_text=response.output_text,
                reason=interpretation.reason or "invalid_or_illegal_move",
                detail=deterministic_explanation,
                fen=fen_before,
            )
            if attempt > self.max_correction_attempts:
                return self._finish_invalid_game(
                    game_id=game_id,
                    board=board,
                    color=color,
                    reason=interpretation.reason or "invalid_or_illegal_move",
                    detail=deterministic_explanation,
                )

        raise RuntimeError("Model turn exited without a result.")

    def _log_provider_error(
        self,
        *,
        game_id: int,
        board: ChessBoard,
        seat: dict[str, Any],
        attempt: int,
        prompt_template: PromptTemplate,
        prompt_kind: str,
        prompt_version: str,
        error: str,
    ) -> None:
        color = board.turn_color
        turn_id = self.repository.log_turn(
            game_id=game_id,
            ply=board.ply,
            attempt=attempt,
            color=color,
            provider=str(seat["provider"]),
            model=str(seat["model"]),
            prompt_kind=prompt_kind,
            prompt_version=prompt_version,
            prompt=prompt_template.prompt,
            instructions=prompt_template.instructions,
            raw_response_text="",
            raw_response_json=None,
            candidate_move=None,
            parsed_move_san=None,
            parsed_move_uci=None,
            fen_before=board.fen,
            fen_after=None,
            is_legal=False,
            latency_ms=None,
            error=error,
        )
        self.repository.log_hallucination(
            game_id=game_id,
            turn_id=turn_id,
            color=color,
            provider=str(seat["provider"]),
            model=str(seat["model"]),
            raw_response_text="",
            candidate_move=None,
            reason="provider_error",
            details=error,
        )
        self.repository.log_game_event(
            game_id=game_id,
            event_type="model_provider_error",
            color=color,
            payload={
                "color": color,
                "provider": seat["provider"],
                "model": seat["model"],
                "error": error,
            },
        )

    def _finish_invalid_game(
        self,
        *,
        game_id: int,
        board: ChessBoard,
        color: str,
        reason: str,
        detail: str,
    ) -> LiveAdvanceResult:
        result = "0-1" if color == "white" else "1-0"
        termination_reason = f"{reason}_{color}"
        self.repository.finish_game(
            game_id,
            status="completed",
            result=result,
            termination_reason=termination_reason,
        )
        self.repository.log_game_event(
            game_id=game_id,
            event_type="game_finished",
            color=color,
            payload={
                "result": result,
                "termination_reason": termination_reason,
                "detail": detail,
                "moves": board.move_history_san(),
            },
        )
        self._emit_referee_message(
            game_id=game_id,
            color=color,
            payload=self.referee_service.finish(
                game_id=game_id,
                result=result,
                termination_reason=termination_reason,
                fen=board.fen,
            ),
        )
        finish_banter = self._finish_banter_payload(
            game_id=game_id,
            result=result,
            termination_reason=termination_reason,
            fen=board.fen,
        )
        if finish_banter is not None:
            self._emit_player_banter(
                game_id=game_id,
                color=color,
                payload=finish_banter,
            )
        self._emit_postgame_showmatch_sequence(
            game_id=game_id,
            result=result,
            termination_reason=termination_reason,
            fen=board.fen,
        )
        return LiveAdvanceResult(
            game_id=game_id,
            status="completed",
            color=color,
            detail=termination_reason,
        )

    def _finish_from_board(self, game_id: int, board: ChessBoard) -> LiveAdvanceResult:
        result = board.result()
        termination_reason = board.outcome_reason()
        self.repository.finish_game(
            game_id,
            status="completed",
            result=result,
            termination_reason=termination_reason,
        )
        self.repository.log_game_event(
            game_id=game_id,
            event_type="game_finished",
            payload={
                "result": result,
                "termination_reason": termination_reason,
                "moves": board.move_history_san(),
            },
        )
        self._emit_referee_message(
            game_id=game_id,
            color=None,
            payload=self.referee_service.finish(
                game_id=game_id,
                result=result,
                termination_reason=termination_reason,
                fen=board.fen,
            ),
        )
        finish_banter = self._finish_banter_payload(
            game_id=game_id,
            result=result,
            termination_reason=termination_reason,
            fen=board.fen,
        )
        if finish_banter is not None:
            self._emit_player_banter(
                game_id=game_id,
                color=None,
                payload=finish_banter,
            )
        self._emit_postgame_showmatch_sequence(
            game_id=game_id,
            result=result,
            termination_reason=termination_reason,
            fen=board.fen,
        )
        return LiveAdvanceResult(
            game_id=game_id,
            status="completed",
            detail=termination_reason,
        )

    def _log_waiting_for_human(
        self,
        game_id: int,
        *,
        color: str,
        ply: int,
        seat: dict[str, Any],
    ) -> None:
        latest_event = self.repository.latest_game_event(game_id)
        latest_payload = (
            latest_event.get("payload_json") if latest_event is not None else None
        )
        if (
            latest_event is not None
            and latest_event["event_type"] == "waiting_for_human_turn"
            and latest_event["color"] == color
            and isinstance(latest_payload, dict)
            and latest_payload.get("ply") == ply
        ):
            return
        self.repository.log_game_event(
            game_id=game_id,
            event_type="waiting_for_human_turn",
            color=color,
            payload={
                "color": color,
                "ply": ply,
                "display_name": seat.get("display_name"),
                "claimed_by": seat.get("claimed_by"),
            },
        )

    def _board_for_game(self, game_id: int) -> ChessBoard:
        game = self._require_game(game_id)
        board = ChessBoard(str(game["initial_fen"]))
        turns = self.repository.list_turns(game_id)
        board.apply_moves_san(accepted_san_moves(turns))
        return board

    def _seat_map(self, game_id: int) -> dict[str, dict[str, Any]]:
        seats = self.repository.list_game_seats(game_id)
        seat_map = {str(seat["color"]): seat for seat in seats}
        if {"white", "black"}.issubset(seat_map):
            return seat_map

        game = self._require_game(game_id)
        for color in ("white", "black"):
            if color in seat_map:
                continue
            seat_map[color] = self.repository.upsert_game_seat(
                game_id=game_id,
                color=color,
                controller=SeatController.MODEL.value,
                provider=str(game[f"{color}_provider"]),
                model=str(game[f"{color}_model"]),
                display_name=f"{game[f'{color}_provider']}:{game[f'{color}_model']}",
                claimed_by=None,
            )
        return seat_map

    def _prompt_for_attempt(
        self,
        *,
        board: ChessBoard,
        legal_moves: tuple[str, ...],
        attempt: int,
        notification: InvalidMoveNotification | None,
        referee_note: str | None,
    ) -> PromptTemplate:
        if attempt == 1 or notification is None:
            return build_benchmark_move_prompt(board, legal_moves)
        return build_invalid_move_retry_prompt(
            board,
            legal_moves,
            notification,
            referee_note=referee_note,
        )

    def _prompt_metadata(
        self,
        provider: MoveProvider,
        prompt_template: PromptTemplate,
    ) -> tuple[str, str]:
        if provider.provider_name == "stockfish":
            return "engine_move", "engine_anchor"
        return prompt_template.kind, prompt_template.version

    def _require_game(self, game_id: int) -> dict[str, Any]:
        game = self.repository.get_game(game_id)
        if game is None:
            raise LookupError(f"Game {game_id} not found.")
        return game

    def _emit_referee_message(
        self,
        *,
        game_id: int,
        color: str | None,
        payload: dict[str, Any],
    ) -> None:
        if not self._referee_enabled(self._require_game(game_id)):
            return
        self.repository.log_game_event(
            game_id=game_id,
            event_type="referee_message",
            color=color,
            payload=payload,
        )

    def _emit_player_banter(
        self,
        *,
        game_id: int,
        color: str | None,
        payload: dict[str, Any],
    ) -> None:
        if not self._banter_enabled(self._require_game(game_id)):
            return
        self.repository.log_game_event(
            game_id=game_id,
            event_type="player_banter",
            color=color,
            payload=payload,
        )

    def _emit_showmatch_script(
        self,
        *,
        game_id: int,
        color: str | None,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self._showmatch_enabled(self._require_game(game_id)):
            return None
        return self.repository.log_game_event(
            game_id=game_id,
            event_type="showmatch_script",
            color=color,
            payload=payload,
        )

    def _referee_enabled(self, game: dict[str, Any]) -> bool:
        return str(game.get("mode") or "benchmark") != "benchmark"

    def _banter_enabled(self, game: dict[str, Any]) -> bool:
        mode = str(game.get("mode") or "benchmark")
        if mode == "benchmark":
            return False
        if mode == "showmatch":
            return self.settings.showmatch_mode.allow_banter
        return True

    def _showmatch_enabled(self, game: dict[str, Any]) -> bool:
        return (
            str(game.get("mode") or "benchmark") == "showmatch"
            and self.settings.showmatch_scripts.enabled
        )

    def _finish_banter_payload(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None = None,
        fen: str = "",
    ) -> dict[str, Any] | None:
        winner, loser = self._winner_and_loser(game_id, result)
        return self.banter_service.finish(
            game_id=game_id,
            winner=winner,
            loser=loser,
            result=result,
            termination_reason=termination_reason,
            fen=fen,
        )

    def _winner_and_loser(
        self,
        game_id: int,
        result: str | None,
    ) -> tuple[str | None, str | None]:
        if result == "1-0":
            return (
                self._seat_speaker_name(game_id, "white"),
                self._seat_speaker_name(game_id, "black"),
            )
        if result == "0-1":
            return (
                self._seat_speaker_name(game_id, "black"),
                self._seat_speaker_name(game_id, "white"),
            )
        return None, None

    def _seat_speaker_name(self, game_id: int, color: str) -> str:
        seat = self._seat_map(game_id)[color]
        return str(
            seat.get("display_name")
            or seat.get("claimed_by")
            or f"{seat['provider']}:{seat['model']}"
        )

    def _opponent_color(self, color: str) -> str:
        return "black" if color == "white" else "white"

    def _showmatch_script_exists(self, game_id: int, *, category: str) -> bool:
        events = self.repository.list_game_events(
            game_id,
            event_types=("showmatch_script",),
            limit=100,
        )
        return any(
            isinstance(event.get("payload_json"), dict)
            and event["payload_json"].get("category") == category
            for event in events
        )

    def _maybe_emit_showmatch_illegal_move_callout(
        self,
        *,
        game_id: int,
        color: str,
        player: str,
        move_text: str | None,
        reason: str,
        detail: str,
        fen: str,
    ) -> None:
        game = self._require_game(game_id)
        if not self._showmatch_enabled(game):
            return
        payload = self.showmatch_script_service.illegal_move_callout(
            game_id=game_id,
            color=color,
            player=player,
            move_text=move_text,
            reason=reason,
            detail=detail,
            fen=fen,
        )
        if payload is not None:
            self._emit_showmatch_script(game_id=game_id, color=color, payload=payload)

    def _maybe_emit_showmatch_hype(
        self,
        *,
        game_id: int,
        color: str,
        speaker: str,
        move: str,
        board: ChessBoard,
    ) -> None:
        game = self._require_game(game_id)
        if not self._showmatch_enabled(game):
            return
        if board.is_game_over():
            return

        tags = self._showmatch_tags(move=move, ply=board.ply)
        if not tags:
            return

        payload = self.showmatch_script_service.midgame_hype(
            game_id=game_id,
            color=color,
            speaker=speaker,
            opponent=self._seat_speaker_name(game_id, self._opponent_color(color)),
            move=move,
            ply=board.ply,
            tags=tags,
            fen=board.fen,
        )
        if payload is not None:
            self._emit_showmatch_script(game_id=game_id, color=color, payload=payload)

    def _showmatch_tags(self, *, move: str, ply: int) -> tuple[str, ...]:
        tags: list[str] = []
        if "x" in move:
            tags.append("capture")
        if "+" in move or "#" in move:
            tags.append("check")
        if "#" in move:
            tags.append("checkmate")
        if "=" in move:
            tags.append("promotion")
        if move.startswith("O-O"):
            tags.append("castle")
        if ply % 10 == 0:
            tags.append("milestone")
        return tuple(tags)

    def _emit_postgame_showmatch_sequence(
        self,
        *,
        game_id: int,
        result: str | None,
        termination_reason: str | None,
        fen: str,
    ) -> None:
        game = self._require_game(game_id)
        if not self._showmatch_enabled(game):
            return
        winner, loser = self._winner_and_loser(game_id, result)
        white_player = self._seat_speaker_name(game_id, "white")
        black_player = self._seat_speaker_name(game_id, "black")

        if not self._showmatch_script_exists(game_id, category="finish"):
            payload = self.showmatch_script_service.finish(
                game_id=game_id,
                result=result,
                termination_reason=termination_reason,
                winner=winner,
                loser=loser,
                fen=fen,
            )
            if payload is not None:
                self._emit_showmatch_script(
                    game_id=game_id, color=None, payload=payload
                )

        if not self._showmatch_script_exists(game_id, category="postgame_interview"):
            for payload in self.showmatch_script_service.postgame_interviews(
                game_id=game_id,
                result=result,
                termination_reason=termination_reason,
                winner=winner,
                loser=loser,
                fen=fen,
            ):
                self._emit_showmatch_script(
                    game_id=game_id,
                    color=None,
                    payload=payload,
                )

        if not self._showmatch_script_exists(game_id, category="rivalry_recap"):
            rivalry_payload = self.showmatch_script_service.rivalry_recap(
                game_id=game_id,
                white_player=white_player,
                black_player=black_player,
                result=result,
                banter_count=self._count_game_events(
                    game_id, event_type="player_banter"
                ),
                illegal_move_count=self._count_illegal_move_events(game_id),
                fen=fen,
            )
            if rivalry_payload is not None:
                self._emit_showmatch_script(
                    game_id=game_id,
                    color=None,
                    payload=rivalry_payload,
                )

        if not self._showmatch_script_exists(game_id, category="quote_pin"):
            quotes = self._quote_candidates(game_id)
            if quotes:
                for payload in self.showmatch_script_service.quote_pins(
                    game_id=game_id,
                    quotes=quotes,
                    fen=fen,
                ):
                    self._emit_showmatch_script(
                        game_id=game_id,
                        color=None,
                        payload=payload,
                    )

    def _count_game_events(self, game_id: int, *, event_type: str) -> int:
        return len(
            self.repository.list_game_events(
                game_id,
                event_types=(event_type,),
                limit=500,
            )
        )

    def _count_illegal_move_events(self, game_id: int) -> int:
        events = self.repository.list_game_events(
            game_id,
            event_types=("showmatch_script",),
            limit=500,
        )
        return sum(
            1
            for event in events
            if isinstance(event.get("payload_json"), dict)
            and event["payload_json"].get("category") == "illegal_move_callout"
        )

    def _quote_candidates(self, game_id: int) -> tuple[QuoteCandidate, ...]:
        player_banter_events = self.repository.list_game_events(
            game_id,
            event_types=("player_banter",),
            limit=100,
        )
        candidates: list[QuoteCandidate] = []
        for event in reversed(player_banter_events):
            payload = event.get("payload_json")
            if not isinstance(payload, dict):
                continue
            message = str(payload.get("message") or "").strip()
            speaker = str(payload.get("speaker") or "").strip()
            if not message or not speaker:
                continue
            candidates.append(
                QuoteCandidate(
                    speaker=speaker,
                    message=message,
                    source_category=str(payload.get("category") or "banter"),
                    event_id=int(event["id"]),
                )
            )
            if len(candidates) == 2:
                break
        return tuple(candidates)


class LiveGameLoopManager:
    def __init__(
        self,
        runtime: InteractiveGameRuntime,
        repository: SQLiteRepository,
        *,
        idle_poll_seconds: float = 0.2,
    ) -> None:
        self.runtime = runtime
        self.repository = repository
        self.idle_poll_seconds = idle_poll_seconds
        self._lock = threading.Lock()
        self._handles: dict[int, _LiveLoopHandle] = {}

    def start(self, game_id: int) -> dict[str, Any]:
        game = self.runtime._require_game(game_id)
        if str(game["status"]) == "completed":
            raise ValueError("Cannot start a completed game.")

        with self._lock:
            handle = self._handles.get(game_id)
            if handle is not None and handle.thread.is_alive():
                return self.status(game_id)

            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._run_loop,
                args=(game_id, stop_event),
                daemon=True,
                name=f"lexichess-live-{game_id}",
            )
            handle = _LiveLoopHandle(
                game_id=game_id,
                thread=thread,
                stop_event=stop_event,
                started_at=time.time(),
            )
            self._handles[game_id] = handle

        self.repository.update_game_status(game_id, status="running")
        self.repository.log_game_event(
            game_id=game_id,
            event_type="live_loop_started",
            payload={"game_id": game_id},
        )
        self.runtime.emit_pregame_intro(game_id)
        thread.start()
        return self.status(game_id)

    def stop(self, game_id: int) -> dict[str, Any]:
        with self._lock:
            handle = self._handles.get(game_id)
            if handle is None:
                return {
                    "game_id": game_id,
                    "running": False,
                    "stop_requested": False,
                    "last_outcome": None,
                    "last_error": None,
                }
            handle.stop_event.set()

        self.repository.log_game_event(
            game_id=game_id,
            event_type="live_loop_stop_requested",
            payload={"game_id": game_id},
        )
        return self.status(game_id)

    def status(self, game_id: int) -> dict[str, Any]:
        with self._lock:
            handle = self._handles.get(game_id)
            if handle is None:
                return {
                    "game_id": game_id,
                    "running": False,
                    "stop_requested": False,
                    "last_outcome": None,
                    "last_error": None,
                }
            return {
                "game_id": game_id,
                "running": handle.thread.is_alive(),
                "stop_requested": handle.stop_event.is_set(),
                "started_at": handle.started_at,
                "last_outcome": handle.last_outcome,
                "last_error": handle.last_error,
            }

    def wait_for_game(self, game_id: int, timeout: float) -> bool:
        with self._lock:
            handle = self._handles.get(game_id)
        if handle is None:
            return True
        handle.thread.join(timeout)
        return not handle.thread.is_alive()

    def _run_loop(self, game_id: int, stop_event: threading.Event) -> None:
        try:
            while not stop_event.is_set():
                outcome = self.runtime.advance_once(game_id)
                self._set_last_outcome(game_id, outcome.status)

                if outcome.status == "completed":
                    return
                if outcome.status == "move_applied":
                    continue

                stop_event.wait(self.idle_poll_seconds)
        except Exception as exc:  # pragma: no cover - defensive worker guard
            self._set_last_error(game_id, str(exc))
            self.repository.log_game_event(
                game_id=game_id,
                event_type="live_loop_failed",
                payload={"game_id": game_id, "error": str(exc)},
            )

    def _set_last_outcome(self, game_id: int, outcome: str) -> None:
        with self._lock:
            handle = self._handles.get(game_id)
            if handle is not None:
                handle.last_outcome = outcome

    def _set_last_error(self, game_id: int, error: str) -> None:
        with self._lock:
            handle = self._handles.get(game_id)
            if handle is not None:
                handle.last_error = error
