from __future__ import annotations

import json
import time
from collections.abc import Iterator
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, cast

import chess
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from lexichess import AppSettings
from lexichess.config import GameMode, ProviderName
from lexichess.index import build_chess_index_snapshot, render_chess_index_markdown
from lexichess.interactive import (
    InteractiveGameRuntime,
    InteractiveGameService,
    LiveGameLoopManager,
    build_banter_service,
    build_broadcast_package,
    build_referee_service,
    build_showmatch_script_service,
)
from lexichess.storage import SQLiteRepository
from lexichess.tournament.export import (
    build_tournament_export,
    render_tournament_markdown,
)
from lexichess.tournament.replay import build_game_bundle

TEMPLATES_DIR = Path(__file__).with_name("templates")
STATIC_DIR = Path(__file__).with_name("static")
BROADCAST_SECTION_CHOICES = (
    "highlights",
    "quotes",
    "showmatch_feed",
    "audio_sync",
    "clips",
    "timeline",
)
MODERATION_ACTION_TO_STATUS = {
    "approve": "approved",
    "suppress": "suppressed",
    "escalate": "escalated",
}


def create_app(settings: AppSettings | None = None) -> FastAPI:
    resolved_settings = settings or AppSettings.from_env()
    repository = SQLiteRepository(resolved_settings.database_path)
    repository.initialize()
    interactive_service = InteractiveGameService(repository, resolved_settings)
    banter_service = build_banter_service(resolved_settings)
    referee_service = build_referee_service(resolved_settings)
    showmatch_script_service = build_showmatch_script_service(resolved_settings)
    interactive_runtime = InteractiveGameRuntime(
        repository,
        resolved_settings,
        banter_service=banter_service,
        referee_service=referee_service,
        showmatch_script_service=showmatch_script_service,
    )
    live_manager = LiveGameLoopManager(interactive_runtime, repository)
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
    app.state.live_manager = live_manager
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
        return _game_bundle(
            repository, interactive_service, live_manager, int(created["game"]["id"])
        )

    @app.get("/api/games/{game_id}")
    def api_game_detail(game_id: int) -> dict[str, Any]:
        return _game_bundle(repository, interactive_service, live_manager, game_id)

    @app.get("/api/games/{game_id}/replay")
    def api_game_replay(game_id: int) -> dict[str, Any]:
        bundle = _game_bundle(repository, interactive_service, live_manager, game_id)
        return {
            "game_id": game_id,
            "moves": bundle["moves"],
            "move_list": bundle["move_list"],
            "pgn": bundle["pgn"],
        }

    @app.post("/api/games/{game_id}/moves", status_code=201)
    def api_submit_human_move(
        game_id: int, payload: HumanMoveRequest
    ) -> dict[str, Any]:
        try:
            event = interactive_runtime.submit_human_move(
                game_id,
                color=payload.color,
                move_text=payload.move_text,
                actor_name=payload.actor_name,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc
        return event

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

    @app.get("/api/games/{game_id}/referee")
    def api_game_referee_events(
        game_id: int,
        after_id: int | None = Query(default=None, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        try:
            return interactive_service.list_events(
                game_id,
                after_id=after_id,
                event_types=("referee_message",),
                limit=limit,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc

    @app.get("/api/games/{game_id}/banter")
    def api_game_banter_events(
        game_id: int,
        after_id: int | None = Query(default=None, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        try:
            return interactive_service.list_events(
                game_id,
                after_id=after_id,
                event_types=("player_banter",),
                limit=limit,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc

    @app.get("/api/games/{game_id}/transcript")
    def api_game_transcript(
        game_id: int,
        after_id: int | None = Query(default=None, ge=0),
        limit: int = Query(default=200, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        try:
            return interactive_service.list_events(
                game_id,
                after_id=after_id,
                event_types=(
                    "referee_message",
                    "player_banter",
                    "showmatch_script",
                    "user_chat",
                    "human_move_submitted",
                    "human_move_rejected",
                ),
                limit=limit,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc

    @app.get("/api/games/{game_id}/showmatch")
    def api_game_showmatch_events(
        game_id: int,
        after_id: int | None = Query(default=None, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        try:
            return interactive_service.list_events(
                game_id,
                after_id=after_id,
                event_types=("showmatch_script",),
                limit=limit,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc

    @app.get("/api/games/{game_id}/quotes")
    def api_game_quote_pin_events(
        game_id: int,
        after_id: int | None = Query(default=None, ge=0),
        limit: int = Query(default=20, ge=1, le=200),
    ) -> list[dict[str, Any]]:
        try:
            events = interactive_service.list_events(
                game_id,
                after_id=after_id,
                event_types=("showmatch_script",),
                limit=200,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc
        return [
            event
            for event in events
            if isinstance(event.get("payload_json"), dict)
            and event["payload_json"].get("category") == "quote_pin"
        ][:limit]

    @app.get("/api/games/{game_id}/broadcast")
    def api_game_broadcast(game_id: int) -> dict[str, Any]:
        bundle = _game_bundle(repository, interactive_service, live_manager, game_id)
        return cast(dict[str, Any], bundle["broadcast"])

    @app.get("/api/games/{game_id}/highlights")
    def api_game_highlights(game_id: int) -> list[dict[str, Any]]:
        bundle = _game_bundle(repository, interactive_service, live_manager, game_id)
        return cast(list[dict[str, Any]], bundle["broadcast_highlights"])

    @app.get("/api/games/{game_id}/clips")
    def api_game_clip_manifest(game_id: int) -> list[dict[str, Any]]:
        bundle = _game_bundle(repository, interactive_service, live_manager, game_id)
        return cast(list[dict[str, Any]], bundle["clip_manifest"])

    @app.get("/api/games/{game_id}/audio-sync")
    def api_game_audio_sync(game_id: int) -> list[dict[str, Any]]:
        bundle = _game_bundle(repository, interactive_service, live_manager, game_id)
        return cast(list[dict[str, Any]], bundle["audio_sync"])

    @app.get("/api/showmatches/featured")
    def api_featured_showmatch() -> dict[str, Any]:
        bundle = _featured_showmatch_bundle(
            repository,
            interactive_service,
            live_manager,
        )
        if bundle is None:
            raise HTTPException(status_code=404, detail="No featured showmatch found.")
        return bundle

    @app.get("/api/showmatches/control")
    def api_showmatch_control() -> dict[str, Any]:
        controls = repository.get_broadcast_controls()
        return {
            "controls": controls,
            "section_choices": list(BROADCAST_SECTION_CHOICES),
            "showmatch_games": _showmatch_games(repository),
        }

    @app.post("/api/showmatches/control/featured")
    def api_set_featured_showmatch(
        payload: FeaturedShowmatchRequest,
    ) -> dict[str, Any]:
        if payload.featured_game_id is not None:
            game = repository.get_game(payload.featured_game_id)
            if game is None:
                raise HTTPException(status_code=404, detail="Game not found.")
            if str(game.get("mode") or "") != "showmatch":
                raise HTTPException(
                    status_code=400,
                    detail="Only showmatch games can be featured.",
                )
        controls = repository.set_featured_showmatch(
            featured_game_id=payload.featured_game_id
        )
        return {"controls": controls}

    @app.post("/api/showmatches/control/clip")
    def api_set_featured_clip(payload: FeaturedClipRequest) -> dict[str, Any]:
        controls = repository.get_broadcast_controls()
        featured_game_id = controls.get("featured_game_id")
        if featured_game_id is None:
            raise HTTPException(
                status_code=400,
                detail="Set a featured showmatch before selecting a clip.",
            )
        featured_bundle = _game_bundle(
            repository,
            interactive_service,
            live_manager,
            int(featured_game_id),
        )
        clip_id = payload.featured_clip_id
        if clip_id is not None and not any(
            clip["clip_id"] == clip_id for clip in featured_bundle["clip_manifest"]
        ):
            raise HTTPException(status_code=400, detail="Clip not found for game.")
        return {"controls": repository.set_featured_clip(featured_clip_id=clip_id)}

    @app.post("/api/showmatches/control/sections")
    def api_set_showmatch_sections(
        payload: BroadcastSectionRequest,
    ) -> dict[str, Any]:
        invalid_sections = [
            section
            for section in payload.enabled_sections
            if section not in BROADCAST_SECTION_CHOICES
        ]
        if invalid_sections:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported broadcast sections: {', '.join(invalid_sections)}",
            )
        return {
            "controls": repository.set_broadcast_enabled_sections(
                payload.enabled_sections
            )
        }

    @app.get("/api/moderation/queue")
    def api_moderation_queue(
        status: str | None = None,
        game_id: int | None = Query(default=None, ge=1),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        statuses = _moderation_status_filter(status)
        return repository.list_moderation_items(
            statuses=statuses,
            game_id=game_id,
            limit=limit,
        )

    @app.post("/api/moderation/queue/{moderation_id}/resolve")
    def api_resolve_moderation_item(
        moderation_id: int,
        payload: ModerationResolveRequest,
    ) -> dict[str, Any]:
        resolved_status = _moderation_status_for_action(payload.action)
        try:
            item = repository.resolve_moderation_item(
                moderation_id,
                status=resolved_status,
                resolution_action=payload.action,
                moderator_name=payload.moderator_name,
                resolution_note=payload.resolution_note,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc
        return {"item": item}

    @app.get("/api/games/{game_id}/live")
    def api_game_live_status(game_id: int) -> dict[str, Any]:
        if repository.get_game(game_id) is None:
            raise HTTPException(status_code=404, detail="Game not found.")
        return live_manager.status(game_id)

    @app.post("/api/games/{game_id}/live/start")
    def api_start_game_live_loop(game_id: int) -> dict[str, Any]:
        try:
            return live_manager.start(game_id)
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc

    @app.post("/api/games/{game_id}/live/stop")
    def api_stop_game_live_loop(game_id: int) -> dict[str, Any]:
        if repository.get_game(game_id) is None:
            raise HTTPException(status_code=404, detail="Game not found.")
        return live_manager.stop(game_id)

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
                event_types=None,
                once=once,
                poll_seconds=poll_seconds,
            ),
            media_type="text/event-stream",
        )

    @app.get("/api/games/{game_id}/referee/stream")
    def api_game_referee_stream(
        game_id: int,
        after_id: int | None = Query(default=None, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
        once: bool = Query(default=False),
        poll_seconds: float = Query(default=5.0, ge=0.0, le=30.0),
    ) -> StreamingResponse:
        try:
            interactive_service.list_events(
                game_id,
                event_types=("referee_message",),
                limit=1,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc
        return StreamingResponse(
            _event_stream(
                interactive_service,
                game_id=game_id,
                after_id=after_id,
                limit=limit,
                event_types=("referee_message",),
                once=once,
                poll_seconds=poll_seconds,
            ),
            media_type="text/event-stream",
        )

    @app.get("/api/games/{game_id}/banter/stream")
    def api_game_banter_stream(
        game_id: int,
        after_id: int | None = Query(default=None, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
        once: bool = Query(default=False),
        poll_seconds: float = Query(default=5.0, ge=0.0, le=30.0),
    ) -> StreamingResponse:
        try:
            interactive_service.list_events(
                game_id,
                event_types=("player_banter",),
                limit=1,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc
        return StreamingResponse(
            _event_stream(
                interactive_service,
                game_id=game_id,
                after_id=after_id,
                limit=limit,
                event_types=("player_banter",),
                once=once,
                poll_seconds=poll_seconds,
            ),
            media_type="text/event-stream",
        )

    @app.get("/api/games/{game_id}/showmatch/stream")
    def api_game_showmatch_stream(
        game_id: int,
        after_id: int | None = Query(default=None, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
        once: bool = Query(default=False),
        poll_seconds: float = Query(default=5.0, ge=0.0, le=30.0),
    ) -> StreamingResponse:
        try:
            interactive_service.list_events(
                game_id,
                event_types=("showmatch_script",),
                limit=1,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc
        return StreamingResponse(
            _event_stream(
                interactive_service,
                game_id=game_id,
                after_id=after_id,
                limit=limit,
                event_types=("showmatch_script",),
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
        bundle = _game_bundle(repository, interactive_service, live_manager, game_id)
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

    @app.get("/showmatches/featured", response_class=HTMLResponse)
    def featured_showmatch_page(request: Request) -> HTMLResponse:
        bundle = _featured_showmatch_bundle(
            repository,
            interactive_service,
            live_manager,
        )
        templates = _templates(request)
        return templates.TemplateResponse(
            request,
            "featured_showmatch.html",
            {
                "request": request,
                "title": "Featured Showmatch",
                "bundle": bundle,
            },
        )

    @app.get("/showmatches/control", response_class=HTMLResponse)
    def showmatch_control_page(request: Request) -> HTMLResponse:
        templates = _templates(request)
        featured_bundle = _featured_showmatch_bundle(
            repository,
            interactive_service,
            live_manager,
        )
        return templates.TemplateResponse(
            request,
            "showmatch_control.html",
            {
                "request": request,
                "title": "Broadcast Control",
                "controls": repository.get_broadcast_controls(),
                "section_choices": list(BROADCAST_SECTION_CHOICES),
                "showmatch_games": _showmatch_games(repository),
                "featured_bundle": featured_bundle,
            },
        )

    @app.get("/moderation/queue", response_class=HTMLResponse)
    def moderation_queue_page(
        request: Request,
        status: str = "pending",
    ) -> HTMLResponse:
        templates = _templates(request)
        statuses = _moderation_status_filter(status)
        return templates.TemplateResponse(
            request,
            "moderation_queue.html",
            {
                "request": request,
                "title": "Moderation Queue",
                "items": repository.list_moderation_items(
                    statuses=statuses,
                    limit=200,
                ),
                "selected_status": status,
                "status_choices": [
                    "pending",
                    "approved",
                    "suppressed",
                    "escalated",
                    "all",
                ],
            },
        )

    @app.get("/showmatches/control/featured", include_in_schema=False)
    def showmatch_control_featured_form(
        featured_game_id: str = "",
    ) -> RedirectResponse:
        normalized_game_id = featured_game_id.strip()
        target_game_id: int | None = None
        if normalized_game_id:
            target_game_id = int(normalized_game_id)
            game = repository.get_game(target_game_id)
            if game is None or str(game.get("mode") or "") != "showmatch":
                raise HTTPException(
                    status_code=400,
                    detail="Only existing showmatch games can be featured.",
                )
        repository.set_featured_showmatch(featured_game_id=target_game_id)
        return RedirectResponse(
            url="/showmatches/control",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.get("/showmatches/control/clip", include_in_schema=False)
    def showmatch_control_clip_form(
        featured_clip_id: str = "",
    ) -> RedirectResponse:
        clip_id = featured_clip_id.strip() or None
        controls = repository.get_broadcast_controls()
        featured_game_id = controls.get("featured_game_id")
        if clip_id is not None and featured_game_id is None:
            raise HTTPException(
                status_code=400,
                detail="Set a featured showmatch before selecting a clip.",
            )
        if clip_id is not None and featured_game_id is not None:
            featured_bundle = _game_bundle(
                repository,
                interactive_service,
                live_manager,
                int(featured_game_id),
            )
            if not any(
                clip["clip_id"] == clip_id for clip in featured_bundle["clip_manifest"]
            ):
                raise HTTPException(status_code=400, detail="Clip not found for game.")
        repository.set_featured_clip(featured_clip_id=clip_id)
        return RedirectResponse(
            url="/showmatches/control",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.get("/showmatches/control/sections", include_in_schema=False)
    def showmatch_control_sections_form(
        enabled_sections: list[str] | None = Query(default=None),
    ) -> RedirectResponse:
        selected_sections = enabled_sections or []
        invalid_sections = [
            section
            for section in selected_sections
            if section not in BROADCAST_SECTION_CHOICES
        ]
        if invalid_sections:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported broadcast sections: {', '.join(invalid_sections)}",
            )
        repository.set_broadcast_enabled_sections(selected_sections)
        return RedirectResponse(
            url="/showmatches/control",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.get("/moderation/queue/{moderation_id}/resolve", include_in_schema=False)
    def moderation_queue_resolve_form(
        moderation_id: int,
        action: str,
        moderator_name: str = "operator",
        resolution_note: str = "",
        status_filter: str = "pending",
    ) -> RedirectResponse:
        resolved_status = _moderation_status_for_action(action)
        try:
            repository.resolve_moderation_item(
                moderation_id,
                status=resolved_status,
                resolution_action=action,
                moderator_name=moderator_name,
                resolution_note=resolution_note or None,
            )
        except (LookupError, ValueError) as exc:
            raise _as_http_error(exc) from exc
        return RedirectResponse(
            url=f"/moderation/queue?status={status_filter}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return app


def _game_bundle(
    repository: SQLiteRepository,
    interactive_service: InteractiveGameService,
    live_manager: LiveGameLoopManager,
    game_id: int,
    *,
    public_view: bool = False,
) -> dict[str, Any]:
    game = repository.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found.")
    turns = repository.list_turns(game_id)
    hallucinations = repository.list_hallucinations(game_id)
    engine_analyses = repository.list_engine_analyses(game_id)
    bundle = build_game_bundle(game, turns, hallucinations, engine_analyses)
    bundle["seats"] = interactive_service.list_seats(game_id)
    all_events = interactive_service.list_events(game_id, limit=500)
    moderation_items = repository.list_moderation_items(game_id=game_id, limit=500)
    suppressed_event_ids = (
        _suppressed_event_ids(moderation_items) if public_view else set()
    )
    visible_events = [
        event for event in all_events if int(event["id"]) not in suppressed_event_ids
    ]
    bundle["events"] = visible_events[-50:]
    bundle["referee_events"] = [
        event for event in visible_events if event["event_type"] == "referee_message"
    ][-20:]
    bundle["banter_events"] = [
        event for event in visible_events if event["event_type"] == "player_banter"
    ][-20:]
    bundle["showmatch_events"] = [
        event for event in visible_events if event["event_type"] == "showmatch_script"
    ][-20:]
    bundle["quote_pin_events"] = [
        event
        for event in bundle["showmatch_events"]
        if isinstance(event.get("payload_json"), dict)
        and event["payload_json"].get("category") == "quote_pin"
    ]
    broadcast = build_broadcast_package(
        game,
        turns,
        hallucinations,
        visible_events,
        seats=cast(list[dict[str, Any]], bundle["seats"]),
    ).to_dict()
    bundle["broadcast"] = broadcast
    bundle["broadcast_timeline"] = broadcast["timeline"]
    bundle["broadcast_highlights"] = broadcast["highlights"]
    bundle["clip_manifest"] = broadcast["clip_manifest"]
    bundle["audio_sync"] = broadcast["audio_sync"]
    bundle["moderation_items"] = moderation_items
    bundle["suppressed_event_ids"] = sorted(suppressed_event_ids)
    bundle["live"] = live_manager.status(game_id)
    return bundle


def _featured_showmatch_bundle(
    repository: SQLiteRepository,
    interactive_service: InteractiveGameService,
    live_manager: LiveGameLoopManager,
) -> dict[str, Any] | None:
    controls = repository.get_broadcast_controls()
    game_id = _featured_showmatch_game_id(repository, controls=controls)
    if game_id is None:
        return None
    bundle = _game_bundle(
        repository,
        interactive_service,
        live_manager,
        game_id,
        public_view=True,
    )
    bundle["broadcast_controls"] = controls
    bundle["visible_sections"] = list(controls.get("enabled_sections", []))
    featured_clip_id = controls.get("featured_clip_id")
    bundle["featured_clip"] = next(
        (
            clip
            for clip in bundle["clip_manifest"]
            if clip["clip_id"] == featured_clip_id
        ),
        None,
    )
    return bundle


def _featured_showmatch_game_id(
    repository: SQLiteRepository,
    *,
    controls: dict[str, Any] | None = None,
) -> int | None:
    resolved_controls = controls or repository.get_broadcast_controls()
    featured_game_id = resolved_controls.get("featured_game_id")
    if featured_game_id is not None:
        game = repository.get_game(int(featured_game_id))
        if game is not None and str(game.get("mode") or "") == "showmatch":
            return int(featured_game_id)
    for game in repository.list_games(limit=200):
        if str(game.get("mode") or "") == "showmatch":
            return int(game["id"])
    return None


def _showmatch_games(repository: SQLiteRepository) -> list[dict[str, Any]]:
    return [
        game
        for game in repository.list_games(limit=100)
        if str(game.get("mode") or "") == "showmatch"
    ]


def _moderation_status_filter(status: str | None) -> tuple[str, ...] | None:
    if status is None:
        return None
    normalized = status.strip().lower()
    if not normalized or normalized == "all":
        return None
    if normalized not in {"pending", "approved", "suppressed", "escalated"}:
        raise HTTPException(status_code=400, detail="Unsupported moderation status.")
    return (normalized,)


def _moderation_status_for_action(action: str) -> str:
    normalized = action.strip().lower()
    resolved_status = MODERATION_ACTION_TO_STATUS.get(normalized)
    if resolved_status is None:
        raise HTTPException(status_code=400, detail="Unsupported moderation action.")
    return resolved_status


def _suppressed_event_ids(moderation_items: list[dict[str, Any]]) -> set[int]:
    return {
        int(item["source_event_id"])
        for item in moderation_items
        if item.get("status") == "suppressed"
        and item.get("source_event_id") is not None
    }


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
    event_types: tuple[str, ...] | None,
    once: bool,
    poll_seconds: float,
) -> Iterator[str]:
    last_seen_id = after_id
    deadline = time.monotonic() + poll_seconds

    while True:
        events = interactive_service.list_events(
            game_id,
            after_id=last_seen_id,
            event_types=event_types,
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


class FeaturedShowmatchRequest(BaseModel):
    featured_game_id: int | None = None


class FeaturedClipRequest(BaseModel):
    featured_clip_id: str | None = None


class BroadcastSectionRequest(BaseModel):
    enabled_sections: list[str] = Field(default_factory=list)


class ModerationResolveRequest(BaseModel):
    action: str
    moderator_name: str | None = None
    resolution_note: str | None = None


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


class HumanMoveRequest(BaseModel):
    color: str
    move_text: str
    actor_name: str | None = None
