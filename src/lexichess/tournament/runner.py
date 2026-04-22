from __future__ import annotations

from lexichess.chess import ChessBoard
from lexichess.llm import MoveProvider, MoveRequest, ProviderError
from lexichess.storage.repository import SQLiteRepository
from lexichess.tournament.models import GameResult

MOVE_SYSTEM_INSTRUCTIONS = (
    "You are playing chess. Reply with exactly one legal move in SAN notation. "
    "Do not include commentary, explanations, or multiple candidate moves."
)


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
    ) -> None:
        self.white_provider = white_provider
        self.black_provider = black_provider
        self.repository = repository
        self.max_plies = max_plies
        self.move_temperature = move_temperature
        self.max_output_tokens = max_output_tokens
        self.log_raw_response_json = log_raw_response_json

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
            color = board.turn_color
            provider = self._provider_for_color(color)
            legal_moves = tuple(board.legal_moves_san())
            prompt = build_move_prompt(board, legal_moves)
            fen_before = board.fen

            request = MoveRequest(
                game_id=game_id,
                move_number=board.ply,
                color=color,
                fen=fen_before,
                prompt=prompt,
                instructions=MOVE_SYSTEM_INSTRUCTIONS,
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
                    color=color,
                    provider=provider.provider_name,
                    model=provider.model,
                    prompt=prompt,
                    instructions=MOVE_SYSTEM_INSTRUCTIONS,
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
                return self._finish_invalid_game(
                    game_id=game_id,
                    moves=moves,
                    color=color,
                    reason="provider_error",
                )

            interpretation = board.parse_move_text(response.output_text)
            fen_after: str | None = None
            is_legal = interpretation.san is not None
            if interpretation.san is not None:
                normalized_move = board.apply_san(interpretation.san)
                fen_after = board.fen
                moves.append(normalized_move)

            turn_id = self.repository.log_turn(
                game_id=game_id,
                ply=request.move_number,
                color=color,
                provider=provider.provider_name,
                model=provider.model,
                prompt=prompt,
                instructions=MOVE_SYSTEM_INSTRUCTIONS,
                raw_response_text=response.output_text,
                raw_response_json=(
                    response.raw_response if self.log_raw_response_json else None
                ),
                candidate_move=interpretation.candidate,
                parsed_move_san=interpretation.san,
                parsed_move_uci=interpretation.uci,
                fen_before=fen_before,
                fen_after=fen_after,
                is_legal=is_legal,
                latency_ms=response.latency_ms,
                error=None if is_legal else interpretation.reason,
            )

            if not is_legal:
                self.repository.log_hallucination(
                    game_id=game_id,
                    turn_id=turn_id,
                    color=color,
                    provider=provider.provider_name,
                    model=provider.model,
                    raw_response_text=response.output_text,
                    candidate_move=interpretation.candidate,
                    reason=interpretation.reason or "invalid_or_illegal_move",
                    details="Response could not be normalized into a legal move.",
                )
                return self._finish_invalid_game(
                    game_id=game_id,
                    moves=moves,
                    color=color,
                    reason=interpretation.reason or "invalid_or_illegal_move",
                )

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

    def _provider_for_color(self, color: str) -> MoveProvider:
        return self.white_provider if color == "white" else self.black_provider

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


def build_move_prompt(board: ChessBoard, legal_moves: tuple[str, ...]) -> str:
    move_history = " ".join(board.move_history_san()) or "None"
    legal_move_list = ", ".join(legal_moves)
    return (
        f"You are playing as {board.turn_color}.\n"
        f"Current FEN: {board.fen}\n"
        f"Moves played so far (SAN): {move_history}\n"
        f"Legal moves available (SAN): {legal_move_list}\n"
        "Return exactly one legal SAN move."
    )
