from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from lexichess.storage import SQLiteRepository
from lexichess.tournament.replay import build_game_bundle


def build_tournament_export(
    repository: SQLiteRepository,
    tournament_id: int,
) -> dict[str, Any]:
    tournament = repository.get_tournament(tournament_id)
    if tournament is None:
        raise ValueError(f"Tournament {tournament_id} was not found.")

    players = repository.list_tournament_players(tournament_id)
    pairings = repository.list_tournament_pairings(tournament_id)
    standings = repository.compute_tournament_standings(tournament_id)

    completed_games: list[dict[str, Any]] = []
    source_game_ids: list[int] = []
    for pairing in pairings:
        game_id = pairing.get("game_id")
        if not isinstance(game_id, int):
            continue
        game = repository.get_game(game_id)
        if game is None:
            continue
        turns = repository.list_turns(game_id)
        hallucinations = repository.list_hallucinations(game_id)
        engine_analyses = repository.list_engine_analyses(game_id)
        completed_games.append(
            {
                "pairing_id": pairing["id"],
                "match_number": pairing["match_number"],
                "round_number": pairing["round_number"],
                "tag": pairing["tag"],
                "rating_updates": repository.list_rating_snapshots_for_game(game_id),
                "game_bundle": build_game_bundle(
                    game,
                    turns,
                    hallucinations,
                    engine_analyses,
                ),
            }
        )
        source_game_ids.append(game_id)

    completed_pairings = [
        pairing for pairing in pairings if pairing["status"] == "completed"
    ]
    failed_pairings = [pairing for pairing in pairings if pairing["status"] == "failed"]
    pending_pairings = [
        pairing for pairing in pairings if pairing["status"] == "pending"
    ]
    running_pairings = [
        pairing for pairing in pairings if pairing["status"] == "running"
    ]

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tournament_id": tournament_id,
        "name": tournament["name"],
        "format": tournament["format"],
        "status": tournament["status"],
        "player_count": len(players),
        "pairing_count": len(pairings),
        "completed_pairings": len(completed_pairings),
        "failed_pairings": len(failed_pairings),
        "pending_pairings": len(pending_pairings),
        "running_pairings": len(running_pairings),
        "source_game_ids": source_game_ids,
        "config": tournament.get("config_json"),
    }
    return {
        "manifest": manifest,
        "tournament": tournament,
        "players": players,
        "pairings": pairings,
        "standings": standings,
        "completed_games": completed_games,
    }


def export_tournament_json(
    repository: SQLiteRepository,
    tournament_id: int,
) -> str:
    return json.dumps(build_tournament_export(repository, tournament_id), indent=2)


def render_tournament_markdown(
    repository: SQLiteRepository,
    tournament_id: int,
) -> str:
    report = build_tournament_export(repository, tournament_id)
    manifest = report["manifest"]
    lines = [
        f"# Tournament Report: {manifest['name']}",
        "",
        f"Generated: {manifest['generated_at']}",
        f"Format: {manifest['format']}",
        f"Status: {manifest['status']}",
        f"Players: {manifest['player_count']}",
        f"Pairings: {manifest['pairing_count']}",
        "",
        "## Standings",
        "",
        "| Rank | Player | Points | W | D | L | Games |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["standings"]:
        lines.append(
            f"| {row['rank']} | {row['label']} | {row['points']:.1f} | "
            f"{row['wins']} | {row['draws']} | {row['losses']} | {row['games_played']} |"
        )

    lines.extend(
        [
            "",
            "## Pairings",
            "",
            "| Match | Round | White | Black | Status | Result | Game |",
            "| --- | ---: | --- | --- | --- | --- | ---: |",
        ]
    )
    for pairing in report["pairings"]:
        lines.append(
            f"| {pairing['match_number']} | {pairing['round_number']} | "
            f"{pairing['white_label']} | {pairing['black_label']} | "
            f"{pairing['status']} | {pairing['result'] or '-'} | {pairing['game_id'] or '-'} |"
        )

    return "\n".join(lines) + "\n"
