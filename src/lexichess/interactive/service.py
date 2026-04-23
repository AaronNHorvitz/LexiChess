from __future__ import annotations

from typing import Any

from lexichess.chess import ChessBoard
from lexichess.config import AppSettings, GameMode, ProviderName, SeatController
from lexichess.storage import SQLiteRepository

_COLORS = ("white", "black")


class InteractiveGameService:
    def __init__(
        self,
        repository: SQLiteRepository,
        settings: AppSettings,
    ) -> None:
        self.repository = repository
        self.settings = settings

    def create_game(
        self,
        *,
        mode: GameMode | str = GameMode.INTERACTIVE,
        initial_fen: str | None = None,
        white_provider: ProviderName | str | None = None,
        white_model: str | None = None,
        white_display_name: str | None = None,
        black_provider: ProviderName | str | None = None,
        black_model: str | None = None,
        black_display_name: str | None = None,
    ) -> dict[str, Any]:
        resolved_mode = (
            mode if isinstance(mode, GameMode) else GameMode(str(mode).lower())
        )
        board = ChessBoard(initial_fen)

        resolved_white_provider = self._normalize_provider(
            white_provider or self.settings.default_provider.value
        )
        resolved_black_provider = self._normalize_provider(
            black_provider or self.settings.default_provider.value
        )
        resolved_white_model = white_model or self.settings.model_for(
            resolved_white_provider
        )
        resolved_black_model = black_model or self.settings.model_for(
            resolved_black_provider
        )

        game_id = self.repository.create_game(
            white_provider=resolved_white_provider,
            white_model=resolved_white_model,
            black_provider=resolved_black_provider,
            black_model=resolved_black_model,
            initial_fen=board.initial_fen,
            mode=resolved_mode.value,
            status="created",
        )

        white_seat = self.repository.upsert_game_seat(
            game_id=game_id,
            color="white",
            controller=SeatController.MODEL.value,
            provider=resolved_white_provider,
            model=resolved_white_model,
            display_name=white_display_name
            or f"{resolved_white_provider}:{resolved_white_model}",
            claimed_by=None,
        )
        black_seat = self.repository.upsert_game_seat(
            game_id=game_id,
            color="black",
            controller=SeatController.MODEL.value,
            provider=resolved_black_provider,
            model=resolved_black_model,
            display_name=black_display_name
            or f"{resolved_black_provider}:{resolved_black_model}",
            claimed_by=None,
        )
        self.repository.log_game_event(
            game_id=game_id,
            event_type="game_created",
            payload={
                "mode": resolved_mode.value,
                "initial_fen": board.initial_fen,
                "seats": {
                    "white": white_seat,
                    "black": black_seat,
                },
            },
        )
        return self.game_state(game_id, events_limit=20)

    def list_seats(self, game_id: int) -> list[dict[str, Any]]:
        game = self._require_game(game_id)
        seats = {
            seat["color"]: seat for seat in self.repository.list_game_seats(game_id)
        }
        for color in _COLORS:
            if color not in seats:
                seats[color] = self.repository.upsert_game_seat(
                    game_id=game_id,
                    color=color,
                    controller=SeatController.MODEL.value,
                    provider=str(game[f"{color}_provider"]),
                    model=str(game[f"{color}_model"]),
                    display_name=f"{game[f'{color}_provider']}:{game[f'{color}_model']}",
                    claimed_by=None,
                )
        return [seats["white"], seats["black"]]

    def claim_seat(
        self,
        game_id: int,
        *,
        color: str,
        claimed_by: str,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        normalized_color = self._normalize_color(color)
        actor = claimed_by.strip()
        if not actor:
            raise ValueError("claimed_by must not be empty.")

        seat = self._seat_for_update(game_id, normalized_color)
        updated_seat = self.repository.upsert_game_seat(
            game_id=game_id,
            color=normalized_color,
            controller=SeatController.HUMAN.value,
            provider=seat.get("provider"),
            model=seat.get("model"),
            display_name=display_name.strip() if display_name else actor,
            claimed_by=actor,
        )
        event = self.repository.log_game_event(
            game_id=game_id,
            event_type="seat_claimed",
            color=normalized_color,
            payload={
                "color": normalized_color,
                "claimed_by": actor,
                "seat": updated_seat,
            },
        )
        return {"seat": updated_seat, "event": event}

    def release_seat_to_model(
        self,
        game_id: int,
        *,
        color: str,
        provider: ProviderName | str | None = None,
        model: str | None = None,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        normalized_color = self._normalize_color(color)
        seat = self._seat_for_update(game_id, normalized_color)
        game = self._require_game(game_id)

        resolved_provider = self._normalize_provider(
            provider
            or seat.get("provider")
            or str(game[f"{normalized_color}_provider"])
        )
        resolved_model = (
            model or seat.get("model") or str(game[f"{normalized_color}_model"])
        )

        updated_seat = self.repository.upsert_game_seat(
            game_id=game_id,
            color=normalized_color,
            controller=SeatController.MODEL.value,
            provider=resolved_provider,
            model=resolved_model,
            display_name=display_name or f"{resolved_provider}:{resolved_model}",
            claimed_by=None,
        )
        event = self.repository.log_game_event(
            game_id=game_id,
            event_type="seat_released_to_model",
            color=normalized_color,
            payload={
                "color": normalized_color,
                "seat": updated_seat,
            },
        )
        return {"seat": updated_seat, "event": event}

    def post_user_chat(
        self,
        game_id: int,
        *,
        author_name: str,
        target: str,
        message: str,
    ) -> dict[str, Any]:
        self._require_game(game_id)
        author = author_name.strip()
        body = message.strip()
        if not author:
            raise ValueError("author_name must not be empty.")
        if not body:
            raise ValueError("message must not be empty.")

        normalized_target = target.strip().lower()
        if not normalized_target:
            raise ValueError("target must not be empty.")

        return self.repository.log_game_event(
            game_id=game_id,
            event_type="user_chat",
            color=normalized_target if normalized_target in _COLORS else None,
            payload={
                "author_name": author,
                "target": normalized_target,
                "message": body,
            },
        )

    def list_events(
        self,
        game_id: int,
        *,
        after_id: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        self._require_game(game_id)
        return self.repository.list_game_events(game_id, after_id=after_id, limit=limit)

    def game_state(self, game_id: int, *, events_limit: int = 50) -> dict[str, Any]:
        game = self._require_game(game_id)
        return {
            "game": game,
            "seats": self.list_seats(game_id),
            "events": self.repository.list_game_events(game_id, limit=events_limit),
        }

    def _seat_for_update(self, game_id: int, color: str) -> dict[str, Any]:
        self._require_game(game_id)
        seat = self.repository.get_game_seat(game_id, color)
        if seat is not None:
            return seat
        return {seat["color"]: seat for seat in self.list_seats(game_id)}[color]

    def _require_game(self, game_id: int) -> dict[str, Any]:
        game = self.repository.get_game(game_id)
        if game is None:
            raise LookupError(f"Game {game_id} not found.")
        return game

    def _normalize_color(self, color: str) -> str:
        normalized = color.strip().lower()
        if normalized not in _COLORS:
            raise ValueError(f"Unsupported seat color: {color}")
        return normalized

    def _normalize_provider(self, provider: ProviderName | str) -> str:
        if isinstance(provider, ProviderName):
            return provider.value
        return ProviderName(str(provider).lower()).value
