from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from lexichess.index.service import identity_from_game
from lexichess.storage import SQLiteRepository


@dataclass(frozen=True, slots=True)
class ChessIndexRow:
    rank: int
    competitor_slug: str
    provider: str
    model: str
    runtime: str
    prompt_profile: str
    quantization: str | None
    hardware_class: str | None
    revision: str | None
    rating: float
    games_played: int
    provisional: bool
    wins: int
    draws: int
    losses: int
    win_rate: float
    last_result: str | None
    last_updated_at: str | None


@dataclass(frozen=True, slots=True)
class ChessIndexSnapshot:
    generated_at: str
    total_competitors: int
    included_competitors: int
    limit: int
    minimum_games: int
    include_provisional: bool
    entries: tuple[ChessIndexRow, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_competitors": self.total_competitors,
            "included_competitors": self.included_competitors,
            "limit": self.limit,
            "minimum_games": self.minimum_games,
            "include_provisional": self.include_provisional,
            "entries": [asdict(entry) for entry in self.entries],
        }


def build_chess_index_snapshot(
    repository: SQLiteRepository,
    *,
    limit: int = 50,
    minimum_games: int = 0,
    include_provisional: bool = True,
) -> ChessIndexSnapshot:
    latest_rows = repository.list_latest_ratings(limit=max(limit * 10, 200))
    game_cache: dict[int, dict[str, Any] | None] = {}
    turn_cache: dict[int, list[dict[str, Any]]] = {}

    included_rows: list[ChessIndexRow] = []
    for row in latest_rows:
        if not include_provisional and bool(row["provisional"]):
            continue
        if int(row["games_played"]) < minimum_games:
            continue

        history = repository.list_rating_history(str(row["competitor_slug"]))
        wins = 0
        draws = 0
        losses = 0
        for history_row in history:
            perspective_result = _resolve_competitor_result(
                repository,
                history_row,
                game_cache=game_cache,
                turn_cache=turn_cache,
            )
            if perspective_result == "win":
                wins += 1
            elif perspective_result == "draw":
                draws += 1
            elif perspective_result == "loss":
                losses += 1

        total_results = wins + draws + losses
        win_rate = wins / total_results if total_results > 0 else 0.0
        included_rows.append(
            ChessIndexRow(
                rank=0,
                competitor_slug=str(row["competitor_slug"]),
                provider=str(row["provider"]),
                model=str(row["model"]),
                runtime=str(row["runtime"]),
                prompt_profile=str(row["prompt_profile"]),
                quantization=_optional_str(row.get("quantization")),
                hardware_class=_optional_str(row.get("hardware_class")),
                revision=_optional_str(row.get("revision")),
                rating=float(row["rating"]),
                games_played=int(row["games_played"]),
                provisional=bool(row["provisional"]),
                wins=wins,
                draws=draws,
                losses=losses,
                win_rate=win_rate,
                last_result=_resolve_competitor_result(
                    repository,
                    row,
                    game_cache=game_cache,
                    turn_cache=turn_cache,
                ),
                last_updated_at=_optional_str(row.get("created_at")),
            )
        )

    ordered_rows = sorted(
        included_rows,
        key=lambda entry: (
            -entry.rating,
            entry.provisional,
            -entry.games_played,
            entry.competitor_slug,
        ),
    )[:limit]

    ranked_rows = tuple(
        ChessIndexRow(
            rank=index,
            competitor_slug=row.competitor_slug,
            provider=row.provider,
            model=row.model,
            runtime=row.runtime,
            prompt_profile=row.prompt_profile,
            quantization=row.quantization,
            hardware_class=row.hardware_class,
            revision=row.revision,
            rating=row.rating,
            games_played=row.games_played,
            provisional=row.provisional,
            wins=row.wins,
            draws=row.draws,
            losses=row.losses,
            win_rate=row.win_rate,
            last_result=row.last_result,
            last_updated_at=row.last_updated_at,
        )
        for index, row in enumerate(ordered_rows, start=1)
    )

    return ChessIndexSnapshot(
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_competitors=len(latest_rows),
        included_competitors=len(ranked_rows),
        limit=limit,
        minimum_games=minimum_games,
        include_provisional=include_provisional,
        entries=ranked_rows,
    )


def render_chess_index_markdown(snapshot: ChessIndexSnapshot) -> str:
    lines = [
        "# LexiChess Chess Index",
        "",
        f"Generated: {snapshot.generated_at}",
        f"Included competitors: {snapshot.included_competitors}/{snapshot.total_competitors}",
        f"Filters: minimum_games={snapshot.minimum_games}, include_provisional={snapshot.include_provisional}",
        "",
        "| Rank | Competitor | Rating | Games | W-D-L | Provisional | Last Result |",
        "| --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for entry in snapshot.entries:
        lines.append(
            f"| {entry.rank} | `{entry.competitor_slug}` | {entry.rating:.1f} | "
            f"{entry.games_played} | {entry.wins}-{entry.draws}-{entry.losses} | "
            f"{'yes' if entry.provisional else 'no'} | {entry.last_result or '-'} |"
        )
    return "\n".join(lines) + "\n"


def _resolve_competitor_result(
    repository: SQLiteRepository,
    row: dict[str, Any],
    *,
    game_cache: dict[int, dict[str, Any] | None],
    turn_cache: dict[int, list[dict[str, Any]]],
) -> str | None:
    stored_result = _optional_str(row.get("competitor_result"))
    if stored_result is not None:
        return stored_result

    source_result = _optional_str(row.get("source_result"))
    if source_result == "1/2-1/2":
        return "draw"

    source_game_id = row.get("source_game_id")
    if not isinstance(source_game_id, int):
        return None

    game = game_cache.setdefault(source_game_id, repository.get_game(source_game_id))
    if game is None:
        return None
    turns = turn_cache.setdefault(source_game_id, repository.list_turns(source_game_id))
    white_slug = identity_from_game(game, turns, color="white").slug
    black_slug = identity_from_game(game, turns, color="black").slug
    competitor_slug = str(row["competitor_slug"])

    if source_result == "1-0":
        if competitor_slug == white_slug:
            return "win"
        if competitor_slug == black_slug:
            return "loss"
    if source_result == "0-1":
        if competitor_slug == white_slug:
            return "loss"
        if competitor_slug == black_slug:
            return "win"
    return None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
