from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Mapping

from lexichess.tournament.replay import accepted_turns


@dataclass(slots=True)
class BroadcastTimelineEntry:
    entry_id: str
    entry_type: str
    category: str
    title: str
    message: str
    created_at: str | None
    sequence: int = 0
    color: str | None = None
    speaker: str | None = None
    move: str | None = None
    ply: int | None = None
    tags: tuple[str, ...] = ()
    source_turn_id: int | None = None
    source_event_id: int | None = None
    source_hallucination_id: int | None = None
    _sort_bucket: int = field(default=0, repr=False)
    _sort_order: int = field(default=0, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "category": self.category,
            "title": self.title,
            "message": self.message,
            "created_at": self.created_at,
            "sequence": self.sequence,
            "color": self.color,
            "speaker": self.speaker,
            "move": self.move,
            "ply": self.ply,
            "tags": list(self.tags),
            "source_turn_id": self.source_turn_id,
            "source_event_id": self.source_event_id,
            "source_hallucination_id": self.source_hallucination_id,
        }


@dataclass(slots=True)
class BroadcastHighlight:
    highlight_id: str
    entry_id: str
    category: str
    severity: str
    title: str
    summary: str
    tags: tuple[str, ...]
    recommended_duration_seconds: int
    timeline_entry_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "highlight_id": self.highlight_id,
            "entry_id": self.entry_id,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "summary": self.summary,
            "tags": list(self.tags),
            "recommended_duration_seconds": self.recommended_duration_seconds,
            "timeline_entry_ids": list(self.timeline_entry_ids),
        }


@dataclass(slots=True)
class BroadcastClip:
    clip_id: str
    title: str
    summary: str
    start_entry_id: str
    end_entry_id: str
    focus_entry_id: str
    tags: tuple[str, ...]
    recommended_duration_seconds: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "title": self.title,
            "summary": self.summary,
            "start_entry_id": self.start_entry_id,
            "end_entry_id": self.end_entry_id,
            "focus_entry_id": self.focus_entry_id,
            "tags": list(self.tags),
            "recommended_duration_seconds": self.recommended_duration_seconds,
        }


@dataclass(slots=True)
class BroadcastPackage:
    timeline: list[BroadcastTimelineEntry]
    highlights: list[BroadcastHighlight]
    clips: list[BroadcastClip]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timeline": [entry.to_dict() for entry in self.timeline],
            "highlights": [highlight.to_dict() for highlight in self.highlights],
            "clip_manifest": [clip.to_dict() for clip in self.clips],
            "summary": {
                "timeline_count": len(self.timeline),
                "highlight_count": len(self.highlights),
                "clip_count": len(self.clips),
            },
        }


def build_broadcast_package(
    game: Mapping[str, Any],
    turns: Sequence[Mapping[str, Any]],
    hallucinations: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
    *,
    seats: Sequence[Mapping[str, Any]] | None = None,
) -> BroadcastPackage:
    speaker_map = _speaker_map(game, seats or [])
    timeline: list[BroadcastTimelineEntry] = []

    for turn in accepted_turns(turns):
        timeline.append(_move_timeline_entry(turn, speaker_map))
    for hallucination in hallucinations:
        timeline.append(_hallucination_timeline_entry(hallucination, speaker_map))
    for event in events:
        entry = _event_timeline_entry(event)
        if entry is not None:
            timeline.append(entry)

    timeline.sort(
        key=lambda entry: (
            entry.created_at or "",
            entry._sort_bucket,
            entry._sort_order,
            entry.entry_id,
        )
    )
    for index, entry in enumerate(timeline, start=1):
        entry.sequence = index

    highlights = _detect_highlights(timeline)
    clips = _build_clip_manifest(timeline, highlights)
    return BroadcastPackage(timeline=timeline, highlights=highlights, clips=clips)


def _speaker_map(
    game: Mapping[str, Any],
    seats: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    speakers = {
        "white": f"{game['white_provider']}:{game['white_model']}",
        "black": f"{game['black_provider']}:{game['black_model']}",
    }
    for seat in seats:
        color = str(seat.get("color") or "")
        display_name = str(seat.get("display_name") or "").strip()
        if color in speakers and display_name:
            speakers[color] = display_name
    return speakers


def _move_timeline_entry(
    turn: Mapping[str, Any],
    speaker_map: Mapping[str, str],
) -> BroadcastTimelineEntry:
    color = str(turn.get("color") or "")
    move = str(turn.get("parsed_move_san") or "")
    speaker = speaker_map.get(color, color.title())
    tags = _move_tags(move)
    title = f"{speaker} plays {move}"
    if "checkmate" in tags:
        title = f"{speaker} delivers checkmate"
    elif "promotion" in tags:
        title = f"{speaker} promotes with {move}"
    elif "check" in tags:
        title = f"{speaker} gives check"
    elif "capture" in tags:
        title = f"{speaker} makes a capture"
    return BroadcastTimelineEntry(
        entry_id=f"turn:{turn['id']}",
        entry_type="move",
        category="move",
        title=title,
        message=f"{speaker} plays {move}.",
        created_at=_optional_str(turn.get("created_at")),
        color=color or None,
        speaker=speaker,
        move=move,
        ply=_optional_int(turn.get("ply")),
        tags=tags,
        source_turn_id=_optional_int(turn.get("id")),
        _sort_bucket=1,
        _sort_order=_optional_int(turn.get("id")) or 0,
    )


def _hallucination_timeline_entry(
    hallucination: Mapping[str, Any],
    speaker_map: Mapping[str, str],
) -> BroadcastTimelineEntry:
    color = str(hallucination.get("color") or "")
    speaker = speaker_map.get(color, color.title())
    message = str(
        hallucination.get("details")
        or hallucination.get("raw_response_text")
        or "Illegal move detected."
    )
    reason = str(hallucination.get("reason") or "invalid_move")
    return BroadcastTimelineEntry(
        entry_id=f"hallucination:{hallucination['id']}",
        entry_type="hallucination",
        category=reason,
        title=f"Illegal move by {speaker}",
        message=message,
        created_at=_optional_str(hallucination.get("created_at")),
        color=color or None,
        speaker=speaker,
        tags=("illegal_move", "hallucination"),
        source_hallucination_id=_optional_int(hallucination.get("id")),
        _sort_bucket=2,
        _sort_order=_optional_int(hallucination.get("id")) or 0,
    )


def _event_timeline_entry(event: Mapping[str, Any]) -> BroadcastTimelineEntry | None:
    payload = event.get("payload_json")
    event_type = str(event.get("event_type") or "")
    event_id = _optional_int(event.get("id")) or 0
    created_at = _optional_str(event.get("created_at"))
    color = _optional_str(event.get("color"))

    if event_type == "referee_message" and isinstance(payload, Mapping):
        speaker = _string_or_none(payload.get("speaker")) or "Referee"
        category = _string_or_none(payload.get("category")) or "referee"
        message = _string_or_none(payload.get("message")) or "Referee message."
        return BroadcastTimelineEntry(
            entry_id=f"event:{event_id}",
            entry_type="referee",
            category=category,
            title=f"{speaker} ruling",
            message=message,
            created_at=created_at,
            color=color,
            speaker=speaker,
            tags=(category,),
            source_event_id=event_id,
            _sort_bucket=3,
            _sort_order=event_id,
        )

    if event_type == "player_banter" and isinstance(payload, Mapping):
        speaker = _string_or_none(payload.get("speaker")) or "Player"
        message = _string_or_none(payload.get("message")) or "Player banter."
        category = _string_or_none(payload.get("category")) or "banter"
        tags = _string_tuple(payload.get("tags")) or (category,)
        return BroadcastTimelineEntry(
            entry_id=f"event:{event_id}",
            entry_type="banter",
            category=category,
            title=f"{speaker} banter",
            message=message,
            created_at=created_at,
            color=color,
            speaker=speaker,
            move=_string_or_none(payload.get("move")),
            tags=tags,
            source_event_id=event_id,
            _sort_bucket=4,
            _sort_order=event_id,
        )

    if event_type == "showmatch_script" and isinstance(payload, Mapping):
        speaker = _string_or_none(payload.get("speaker")) or "Arena Booth"
        category = _string_or_none(payload.get("category")) or "showmatch"
        message = _string_or_none(payload.get("message")) or "Showmatch beat."
        return BroadcastTimelineEntry(
            entry_id=f"event:{event_id}",
            entry_type="showmatch",
            category=category,
            title=f"{speaker} {category.replace('_', ' ')}",
            message=message,
            created_at=created_at,
            color=color,
            speaker=speaker,
            move=_string_or_none(payload.get("move")),
            ply=_optional_int(payload.get("ply")),
            tags=_string_tuple(payload.get("tags")) or (category,),
            source_event_id=event_id,
            _sort_bucket=5,
            _sort_order=event_id,
        )

    if event_type == "user_chat" and isinstance(payload, Mapping):
        speaker = _string_or_none(payload.get("author_name")) or "Audience"
        message = _string_or_none(payload.get("message")) or "User chat."
        return BroadcastTimelineEntry(
            entry_id=f"event:{event_id}",
            entry_type="chat",
            category="user_chat",
            title=f"{speaker} joins the conversation",
            message=message,
            created_at=created_at,
            color=color,
            speaker=speaker,
            tags=("chat",),
            source_event_id=event_id,
            _sort_bucket=6,
            _sort_order=event_id,
        )

    if event_type == "game_finished" and isinstance(payload, Mapping):
        result = _string_or_none(payload.get("result")) or "*"
        reason = _string_or_none(payload.get("termination_reason")) or "game_over"
        return BroadcastTimelineEntry(
            entry_id=f"event:{event_id}",
            entry_type="system",
            category="game_finished",
            title="Game finished",
            message=f"Game ends with result {result} via {reason}.",
            created_at=created_at,
            color=color,
            tags=("finish",),
            source_event_id=event_id,
            _sort_bucket=7,
            _sort_order=event_id,
        )

    return None


def _detect_highlights(
    timeline: list[BroadcastTimelineEntry],
) -> list[BroadcastHighlight]:
    highlights: list[BroadcastHighlight] = []
    for index, entry in enumerate(timeline):
        if entry.entry_type == "hallucination":
            highlights.append(
                _highlight_from_entry(
                    entry,
                    index=index,
                    category="illegal_move",
                    severity="high",
                    duration=16,
                )
            )
        elif entry.entry_type == "move" and "checkmate" in entry.tags:
            highlights.append(
                _highlight_from_entry(
                    entry,
                    index=index,
                    category="checkmate",
                    severity="critical",
                    duration=22,
                )
            )
        elif entry.entry_type == "move" and "promotion" in entry.tags:
            highlights.append(
                _highlight_from_entry(
                    entry,
                    index=index,
                    category="promotion",
                    severity="high",
                    duration=18,
                )
            )
        elif entry.entry_type == "move" and "check" in entry.tags:
            highlights.append(
                _highlight_from_entry(
                    entry,
                    index=index,
                    category="check",
                    severity="medium",
                    duration=12,
                )
            )
        elif entry.entry_type == "showmatch" and entry.category in {
            "illegal_move_callout",
            "finish",
            "postgame_interview",
            "rivalry_recap",
            "quote_pin",
        }:
            severity = "medium"
            duration = 14
            if entry.category == "finish":
                severity = "high"
                duration = 18
            highlights.append(
                _highlight_from_entry(
                    entry,
                    index=index,
                    category=entry.category,
                    severity=severity,
                    duration=duration,
                )
            )
    return highlights[:12]


def _highlight_from_entry(
    entry: BroadcastTimelineEntry,
    *,
    index: int,
    category: str,
    severity: str,
    duration: int,
) -> BroadcastHighlight:
    related_ids = [entry.entry_id]
    return BroadcastHighlight(
        highlight_id=f"highlight:{index + 1}",
        entry_id=entry.entry_id,
        category=category,
        severity=severity,
        title=entry.title,
        summary=entry.message,
        tags=entry.tags,
        recommended_duration_seconds=duration,
        timeline_entry_ids=tuple(related_ids),
    )


def _build_clip_manifest(
    timeline: list[BroadcastTimelineEntry],
    highlights: list[BroadcastHighlight],
) -> list[BroadcastClip]:
    if not timeline:
        return []
    index_by_entry_id = {entry.entry_id: idx for idx, entry in enumerate(timeline)}
    clips: list[BroadcastClip] = []
    for highlight in highlights:
        focus_index = index_by_entry_id.get(highlight.entry_id)
        if focus_index is None:
            continue
        start_index = max(focus_index - 1, 0)
        end_index = min(focus_index + 1, len(timeline) - 1)
        clips.append(
            BroadcastClip(
                clip_id=f"clip:{highlight.highlight_id}",
                title=highlight.title,
                summary=highlight.summary,
                start_entry_id=timeline[start_index].entry_id,
                end_entry_id=timeline[end_index].entry_id,
                focus_entry_id=highlight.entry_id,
                tags=highlight.tags,
                recommended_duration_seconds=highlight.recommended_duration_seconds,
            )
        )
    return clips


def _move_tags(move: str) -> tuple[str, ...]:
    tags: list[str] = []
    if "x" in move:
        tags.append("capture")
    if "+" in move:
        tags.append("check")
    if "#" in move:
        tags.append("checkmate")
    if "=" in move:
        tags.append("promotion")
    if move.startswith("O-O"):
        tags.append("castle")
    return tuple(tags)


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
