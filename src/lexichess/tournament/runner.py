from __future__ import annotations

from collections.abc import Callable

from lexichess.analysis import StockfishEngine
from lexichess.chess import ChessBoard
from lexichess.llm import MoveProvider, MoveRequest, ProviderError
from lexichess.storage.repository import SQLiteRepository
from lexichess.tournament.models import GameResult, InvalidMoveNotification
from lexichess.tournament.prompts import (
    PromptTemplate,
    build_benchmark_move_prompt,
    build_invalid_move_retry_prompt,
)

RefereeCallback = Callable[[InvalidMoveNotification], str | None]


class GameRunner:
    def __init__(
        self,
        *,
        white_provider: MoveProvider,
        black_provider: MoveProvider,
        repository: SQLiteRepository,
        max_plies: int = 200,
        move_temperature: float = 0.2,
        max_output_tokens: int = 64,
        log_raw_response_json: bool = True,
        max_correction_attempts: int = 1,
        referee_callback: RefereeCallback | None = None,
        analysis_engine: StockfishEngine | None = None,
    ) -> None:
        self.white_provider = white_provider
        self.black_provider = black_provider
        self.repository = repository
        self.max_plies = max_plies
        self.move_temperature = move_temperature
        self.max_output_tokens = max_output_tokens
        self.log_raw_response_json = log_raw_response_json
        self.max_correction_attempts = max_correction_attempts
        self.referee_callback = referee_callback
        self.analysis_engine = analysis_engine

    def play(self, *, initial_fen: str | None = None) -> GameResult:
        self.repository.initialize()

        board = ChessBoard(initial_fen)
        game_id = self.repository.create_game(
            white_provider=self.white_provider.provider_name,
            white_model=self.white_provider.model,
            black_provider=self.black_provider.provider_name,
            black_model=self.black_provider.model,
            initial_fen=board.fen,
        )

        moves: list[str] = []
        while len(moves) < self.max_plies and not board.is_game_over():
            accepted_move, terminal_result = self._play_turn(
                game_id=game_id, board=board
            )
            if terminal_result is not None:
                return terminal_result
            if accepted_move is not None:
                moves.append(accepted_move)

        if board.is_game_over():
            result = GameResult(
                game_id=game_id,
                status="completed",
                result=board.result(),
                termination_reason=board.outcome_reason(),
                moves=tuple(moves),
            )
            self.repository.finish_game(
                game_id,
                status=result.status,
                result=result.result,
                termination_reason=result.termination_reason,
            )
            return result

        result = GameResult(
            game_id=game_id,
            status="stopped",
            result=None,
            termination_reason="max_plies_reached",
            moves=tuple(moves),
        )
        self.repository.finish_game(
            game_id,
            status=result.status,
            result=result.result,
            termination_reason=result.termination_reason,
        )
        return result

    def _play_turn(
        self,
        *,
        game_id: int,
        board: ChessBoard,
    ) -> tuple[str | None, GameResult | None]:
        color = board.turn_color
        provider = self._provider_for_color(color)
        legal_moves = tuple(board.legal_moves_san())
        fen_before = board.fen

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
                temperature=self.move_temperature,
                max_output_tokens=self.max_output_tokens,
            )

            try:
                response = provider.request_move(request)
            except ProviderError as exc:
                turn_id = self.repository.log_turn(
                    game_id=game_id,
                    ply=board.ply,
                    attempt=attempt,
                    color=color,
                    provider=provider.provider_name,
                    model=provider.model,
                    prompt_kind=prompt_kind,
                    prompt_version=prompt_version,
                    prompt=prompt_template.prompt,
                    instructions=prompt_template.instructions,
                    raw_response_text="",
                    raw_response_json=None,
                    candidate_move=None,
                    parsed_move_san=None,
                    parsed_move_uci=None,
                    fen_before=fen_before,
                    fen_after=None,
                    is_legal=False,
                    latency_ms=None,
                    error=str(exc),
                )
                self.repository.log_hallucination(
                    game_id=game_id,
                    turn_id=turn_id,
                    color=color,
                    provider=provider.provider_name,
                    model=provider.model,
                    raw_response_text="",
                    candidate_move=None,
                    reason="provider_error",
                    details=str(exc),
                )
                return None, self._finish_invalid_game(
                    game_id=game_id,
                    moves=board.move_history_san(),
                    color=color,
                    reason="provider_error",
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
                        response.raw_response if self.log_raw_response_json else None
                    ),
                    candidate_move=interpretation.candidate,
                    parsed_move_san=interpretation.san,
                    parsed_move_uci=interpretation.uci,
                    fen_before=fen_before,
                    fen_after=board.fen,
                    is_legal=True,
                    latency_ms=response.latency_ms,
                    error=None,
                    referee_note=referee_note,
                )
                self._record_engine_analysis(
                    game_id=game_id,
                    turn_id=turn_id,
                    ply=request.move_number,
                    analyzed_fen=board.fen,
                )
                return normalized_move, None

            deterministic_explanation = board.describe_interpretation_failure(
                interpretation
            )
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
            referee_note = self._notify_referee(last_notification)

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
                    response.raw_response if self.log_raw_response_json else None
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

            if attempt > self.max_correction_attempts:
                return None, self._finish_invalid_game(
                    game_id=game_id,
                    moves=board.move_history_san(),
                    color=color,
                    reason=interpretation.reason or "invalid_or_illegal_move",
                )

        raise RuntimeError("Turn loop exited without producing a result.")

    def _prompt_metadata(
        self,
        provider: MoveProvider,
        prompt_template: PromptTemplate,
    ) -> tuple[str, str]:
        if provider.provider_name == "stockfish":
            return "engine_move", "engine_anchor"
        if provider.provider_name == "lexi_engine":
            return "engine_move", "engine_personality"
        return prompt_template.kind, prompt_template.version

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

    def _provider_for_color(self, color: str) -> MoveProvider:
        return self.white_provider if color == "white" else self.black_provider

    def _record_engine_analysis(
        self,
        *,
        game_id: int,
        turn_id: int,
        ply: int,
        analyzed_fen: str,
    ) -> None:
        if self.analysis_engine is None:
            return
        try:
            lines = self.analysis_engine.analyze(analyzed_fen)
        except Exception:  # pragma: no cover - optional enrichment path
            return
        self.repository.log_engine_analysis(
            game_id=game_id,
            turn_id=turn_id,
            ply=ply,
            analyzed_fen=analyzed_fen,
            engine_path=self.analysis_engine.path,
            engine_depth=self.analysis_engine.depth,
            engine_multipv=self.analysis_engine.multipv,
            engine_movetime_ms=self.analysis_engine.movetime_ms,
            lines=lines,
        )

    def _notify_referee(self, notification: InvalidMoveNotification) -> str | None:
        if self.referee_callback is None:
            return None
        try:
            return self.referee_callback(notification)
        except Exception as exc:  # pragma: no cover - defensive product guardrail
            return f"Referee callback failed: {exc}"

    def _finish_invalid_game(
        self,
        *,
        game_id: int,
        moves: list[str],
        color: str,
        reason: str,
    ) -> GameResult:
        result = "0-1" if color == "white" else "1-0"
        game_result = GameResult(
            game_id=game_id,
            status="completed",
            result=result,
            termination_reason=f"{reason}_{color}",
            moves=tuple(moves),
        )
        self.repository.finish_game(
            game_id,
            status=game_result.status,
            result=game_result.result,
            termination_reason=game_result.termination_reason,
        )
        return game_result
