from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

MODERATION_EVENT_TYPES = ("player_banter", "showmatch_script", "referee_message")
HIGH_RISK_KEYWORDS = (
    "kill",
    "die",
    "idiot",
    "stupid",
    "hate",
    "loser",
    "moron",
)


@dataclass(frozen=True, slots=True)
class ModerationCandidate:
    event_type: str
    speaker: str | None
    message: str
    severity: str
    reason_tags: tuple[str, ...]

    def to_record(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "speaker": self.speaker,
            "message": self.message,
            "severity": self.severity,
            "reason_tags": list(self.reason_tags),
        }


def moderation_candidate_for_event(
    *,
    event_type: str,
    payload: Mapping[str, Any],
) -> ModerationCandidate | None:
    if event_type not in MODERATION_EVENT_TYPES:
        return None

    message = str(payload.get("message") or "").strip()
    if not message:
        return None

    speaker = _optional_text(payload.get("speaker"))
    reason_tags: list[str] = []
    severity = "low"

    if event_type == "player_banter":
        reason_tags.extend(("player_banter", "roast_content"))
        severity = "medium"
    elif event_type == "showmatch_script":
        category = _optional_text(payload.get("category")) or "showmatch"
        reason_tags.extend(("showmatch_script", category))
        if category in {
            "illegal_move_callout",
            "postgame_interview",
            "rivalry_recap",
            "quote_pin",
        }:
            severity = "medium"
    elif event_type == "referee_message":
        category = _optional_text(payload.get("category")) or "referee"
        reason_tags.extend(("referee_message", category))

    lowered_message = message.lower()
    for keyword in HIGH_RISK_KEYWORDS:
        if keyword in lowered_message:
            reason_tags.append(f"keyword:{keyword}")
            severity = "high"

    return ModerationCandidate(
        event_type=event_type,
        speaker=speaker,
        message=message,
        severity=severity,
        reason_tags=tuple(reason_tags),
    )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
