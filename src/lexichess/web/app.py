from __future__ import annotations

import json
import time
from collections.abc import Iterator
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, cast

import chess
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from lexichess import AppSettings
from lexichess.config import GameMode, ProviderName
from lexichess.index import build_chess_index_snapshot, render_chess_index_markdown
from lexichess.interactive import InteractiveGameService
from lexichess.storage import SQLiteRepository
from lexichess.tournament.export import (
    build_tournament_export,
    render_tournament_markdown,
)
from lexichess.tournament.replay import build_game_bundle

TEMPLATES_DIR = Path(__file__).with_name("templates")
STATIC_DIR = Path(__file__).with_name("static")


def create_app(settings: AppSettings | None = None) -> FastAPI:
    resolved_settings = settings or AppSettings.from_env()
    repository = SQLiteRepository(resolved_settings.database_path)
    repository.initialize()
    interactive_service = InteractiveGameService(repository, resolved_settings)
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    app = FastAPI(
        title="LexiChess Web",
        version=_package_version(),
        summary="LexiChess API and spectator UI for benchmark data and interactive control.",
    )
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.state.settings = resolved_settings
    app.state.repository = repository
    app.state.interactive_service = interactive_service
    app.state.templates = templates

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {
            "status": "ok",
            "database_path": str(resolved_settings.database_path),
        }

    @app.get("/version")
    def version_payload() -> dict[str, Any]:
        return {"version": _package_version()}

    @app.get("/api/leaderboard")
    def api_leaderboard(
        limit: int = Query(default=50, ge=1, le=500),
        minimum_games: int = Query(default=0, ge=0),
        include_provisional: bool = Query(default=False),
    ) -> dict[str, Any]:
        snapshot = build_chess_index_snapshot(
            repository,
            limit=limit,
            minimum_games=minimum_games,
            include_provisional=include_provisional,
        )
        return snapshot.to_dict()

    @app.get("/api/leaderboard/report", response_class=PlainTextResponse)
    def api_leaderboard_report(
        limit: int = Query(default=50, ge=1, le=500),
        minimum_games: int = Query(default=0, ge=0),
        include_provisional: bool = Query(default=False),
    ) -> str:
        snapshot = build_chess_index_snapshot(
            repository,
            limit=limit,
            minimum_games=minimum_games,
            include_provisional=include_provisional,
        )
        return render_chess_index_markdown(snapshot)

    @app.get("/api/tournaments")
    def api_tournaments(
        status: str | None = None,
        limit: int = Query(default=20, ge=1, le=200),
    ) -> list[dict[str, Any]]:
        return repository.list_tournaments(status=status, limit=limit)

    @app.get("/api/tournaments/{tournament_id}")
    def api_tournament_detail(tournament_id: int) -> dict[str, Any]:
        tournament = repository.get_tournament(tournament_id)
        if tournament is None:
            raise HTTPException(status_code=404, detail="Tournament not found.")
        return _tournament_bundle(repository, tournament)

    @app.get("/api/tournaments/{tournament_id}/report")
    def api_tournament_report(tournament_id: int) -> dict[str, Any]:
        try:
            return build_tournament_export(repository, tournament_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/api/tournaments/{tournament_id}/report.md",
        response_class=PlainTextResponse,
    )
    def api_tournament_report_markdown(tournament_id: int) -> str:
        try:
            return render_tournament_markdown(repository, tournament_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/games")
    def api_games(limit: int = Query(default=20, ge=1, le=200)) -> list[dict[str, Any]]:
        return repository.list_games(limit=limit)

    @app.post("/api/games", status_code=201)
    def api_create_game(payload: GameCreateRequest) -> dict[str, Any]:
        try:
            created = interactive_service.create_game(
                mode=payload.mode,
                initial_fen=payload.initial_fen,
                white_provider=payload.white_provider,
                white_model=payload.white_model,
                white_display_name=payload.white_display_name,
                black_provider=payload.black_provider,
                black_model=payload.black_model,
                black_display_name=payload.black_display_name,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc
        return _game_bundle(repository, interactive_service, int(created["game"]["id"]))

    @app.get("/api/games/{game_id}")
    def api_game_detail(game_id: int) -> dict[str, Any]:
        return _game_bundle(repository, interactive_service, game_id)

    @app.get("/api/games/{game_id}/replay")
    def api_game_replay(game_id: int) -> dict[str, Any]:
        bundle = _game_bundle(repository, interactive_service, game_id)
        return {
            "game_id": game_id,
            "moves": bundle["moves"],
            "move_list": bundle["move_list"],
            "pgn": bundle["pgn"],
        }

    @app.get("/api/games/{game_id}/seats")
    def api_game_seats(game_id: int) -> list[dict[str, Any]]:
        try:
            return interactive_service.list_seats(game_id)
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc

    @app.post("/api/games/{game_id}/seats/{color}/claim")
    def api_claim_game_seat(
        game_id: int,
        color: str,
        payload: SeatClaimRequest,
    ) -> dict[str, Any]:
        try:
            return interactive_service.claim_seat(
                game_id,
                color=color,
                claimed_by=payload.claimed_by,
                display_name=payload.display_name,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc

    @app.post("/api/games/{game_id}/seats/{color}/release")
    def api_release_game_seat(
        game_id: int,
        color: str,
        payload: SeatReleaseRequest,
    ) -> dict[str, Any]:
        try:
            return interactive_service.release_seat_to_model(
                game_id,
                color=color,
                provider=payload.provider,
                model=payload.model,
                display_name=payload.display_name,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc

    @app.get("/api/games/{game_id}/events")
    def api_game_events(
        game_id: int,
        after_id: int | None = Query(default=None, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        try:
            return interactive_service.list_events(
                game_id, after_id=after_id, limit=limit
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc

    @app.get("/api/games/{game_id}/events/stream")
    def api_game_events_stream(
        game_id: int,
        after_id: int | None = Query(default=None, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
        once: bool = Query(default=False),
        poll_seconds: float = Query(default=5.0, ge=0.0, le=30.0),
    ) -> StreamingResponse:
        try:
            interactive_service.list_events(game_id, limit=1)
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc
        return StreamingResponse(
            _event_stream(
                interactive_service,
                game_id=game_id,
                after_id=after_id,
                limit=limit,
                once=once,
                poll_seconds=poll_seconds,
            ),
            media_type="text/event-stream",
        )

    @app.post("/api/games/{game_id}/chat", status_code=201)
    def api_post_game_chat(game_id: int, payload: GameChatRequest) -> dict[str, Any]:
        try:
            return interactive_service.post_user_chat(
                game_id,
                author_name=payload.author_name,
                target=payload.target,
                message=payload.message,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc

    @app.get("/", response_class=HTMLResponse)
    def home_page(request: Request) -> HTMLResponse:
        leaderboard = build_chess_index_snapshot(
            repository,
            limit=8,
            include_provisional=True,
        )
        tournaments = repository.list_tournaments(limit=6)
        games = repository.list_games(limit=6)
        templates = _templates(request)
        return templates.TemplateResponse(
            request,
            "home.html",
            {
                "request": request,
                "title": "LexiChess Arena",
                "leaderboard": leaderboard.entries,
                "tournaments": tournaments,
                "games": games,
                "app_version": _package_version(),
            },
        )

    @app.get("/leaderboard", response_class=HTMLResponse)
    def leaderboard_page(request: Request) -> HTMLResponse:
        snapshot = build_chess_index_snapshot(
            repository,
            limit=50,
            include_provisional=True,
        )
        templates = _templates(request)
        return templates.TemplateResponse(
            request,
            "leaderboard.html",
            {
                "request": request,
                "title": "Chess Index",
                "snapshot": snapshot,
            },
        )

    @app.get("/tournaments", response_class=HTMLResponse)
    def tournaments_page(request: Request) -> HTMLResponse:
        tournaments = repository.list_tournaments(limit=50)
        templates = _templates(request)
        return templates.TemplateResponse(
            request,
            "tournaments.html",
            {
                "request": request,
                "title": "Tournaments",
                "tournaments": tournaments,
            },
        )

    @app.get("/tournaments/{tournament_id}", response_class=HTMLResponse)
    def tournament_page(request: Request, tournament_id: int) -> HTMLResponse:
        tournament = repository.get_tournament(tournament_id)
        if tournament is None:
            raise HTTPException(status_code=404, detail="Tournament not found.")
        bundle = _tournament_bundle(repository, tournament)
        templates = _templates(request)
        return templates.TemplateResponse(
            request,
            "tournament_detail.html",
            {
                "request": request,
                "title": tournament["name"],
                "bundle": bundle,
            },
        )

    @app.get("/games/{game_id}", response_class=HTMLResponse)
    def game_page(request: Request, game_id: int) -> HTMLResponse:
        bundle = _game_bundle(repository, interactive_service, game_id)
        templates = _templates(request)
        return templates.TemplateResponse(
            request,
            "game_detail.html",
            {
                "request": request,
                "title": f"Game {game_id}",
                "bundle": bundle,
            },
        )

    return app


def _game_bundle(
    repository: SQLiteRepository,
    interactive_service: InteractiveGameService,
    game_id: int,
) -> dict[str, Any]:
    game = repository.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found.")
    turns = repository.list_turns(game_id)
    hallucinations = repository.list_hallucinations(game_id)
    engine_analyses = repository.list_engine_analyses(game_id)
    bundle = build_game_bundle(game, turns, hallucinations, engine_analyses)
    bundle["seats"] = interactive_service.list_seats(game_id)
    bundle["events"] = interactive_service.list_events(game_id, limit=50)
    return bundle


def _tournament_bundle(
    repository: SQLiteRepository,
    tournament: dict[str, Any],
) -> dict[str, Any]:
    tournament_id = int(tournament["id"])
    return {
        "tournament": tournament,
        "players": repository.list_tournament_players(tournament_id),
        "pairings": repository.list_tournament_pairings(tournament_id),
        "standings": repository.compute_tournament_standings(tournament_id),
    }


def _templates(request: Request) -> Jinja2Templates:
    return cast(Jinja2Templates, request.app.state.templates)


def _event_stream(
    interactive_service: InteractiveGameService,
    *,
    game_id: int,
    after_id: int | None,
    limit: int,
    once: bool,
    poll_seconds: float,
) -> Iterator[str]:
    last_seen_id = after_id
    deadline = time.monotonic() + poll_seconds

    while True:
        events = interactive_service.list_events(
            game_id,
            after_id=last_seen_id,
            limit=limit,
        )
        if events:
            for event in events:
                last_seen_id = int(event["id"])
                yield _sse_frame(
                    event_type=str(event["event_type"]),
                    event_id=int(event["id"]),
                    payload=event,
                )
            if once:
                break
            continue

        if once:
            yield ": idle\n\n"
            break

        if time.monotonic() >= deadline:
            yield ": keepalive\n\n"
            break

        time.sleep(0.25)


def _sse_frame(*, event_type: str, event_id: int, payload: dict[str, Any]) -> str:
    return (
        f"id: {event_id}\n"
        f"event: {event_type}\n"
        f"data: {json.dumps(payload, sort_keys=True)}\n\n"
    )


def _as_http_error(exc: LookupError | ValueError) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _package_version() -> str:
    try:
        return version("lexichess")
    except PackageNotFoundError:
        return "0.1.0-dev"


class GameCreateRequest(BaseModel):
    mode: GameMode = GameMode.INTERACTIVE
    initial_fen: str = Field(default=chess.STARTING_FEN)
    white_provider: ProviderName | None = None
    white_model: str | None = None
    white_display_name: str | None = None
    black_provider: ProviderName | None = None
    black_model: str | None = None
    black_display_name: str | None = None


class SeatClaimRequest(BaseModel):
    claimed_by: str
    display_name: str | None = None


class SeatReleaseRequest(BaseModel):
    provider: ProviderName | None = None
    model: str | None = None
    display_name: str | None = None


class GameChatRequest(BaseModel):
    author_name: str
    target: str
    message: str
