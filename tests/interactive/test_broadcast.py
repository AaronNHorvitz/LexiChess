from __future__ import annotations

from lexichess.interactive import build_broadcast_package


def test_build_broadcast_package_creates_timeline_highlights_and_clips() -> None:
    game = {
        "id": 7,
        "white_provider": "ollama",
        "white_model": "qwen3:8b",
        "black_provider": "ollama",
        "black_model": "qwen3:14b",
    }
    turns = [
        {
            "id": 11,
            "ply": 1,
            "color": "white",
            "parsed_move_san": "Qxh7+",
            "is_legal": True,
            "created_at": "2026-04-24 10:00:00",
        },
        {
            "id": 12,
            "ply": 2,
            "color": "black",
            "parsed_move_san": "Kxh7",
            "is_legal": True,
            "created_at": "2026-04-24 10:00:01",
        },
    ]
    hallucinations = [
        {
            "id": 5,
            "color": "black",
            "reason": "no_candidate_found",
            "details": "Black tried to play banana instead of a move.",
            "created_at": "2026-04-24 10:00:02",
        }
    ]
    events = [
        {
            "id": 20,
            "event_type": "player_banter",
            "color": "white",
            "created_at": "2026-04-24 10:00:03",
            "payload_json": {
                "speaker": "Qwen Hero",
                "message": "That king is already filing a complaint.",
                "category": "move_reaction",
                "tags": ["banter", "attack"],
                "move": "Qxh7+",
            },
        },
        {
            "id": 21,
            "event_type": "showmatch_script",
            "color": None,
            "created_at": "2026-04-24 10:00:04",
            "payload_json": {
                "speaker": "Arena Booth",
                "category": "finish",
                "message": "The arena has seen enough nonsense for one night.",
                "tags": ["finish"],
            },
        },
    ]

    package = build_broadcast_package(
        game,
        turns,
        hallucinations,
        events,
        seats=[
            {"color": "white", "display_name": "Qwen Hero"},
            {"color": "black", "display_name": "Qwen Villain"},
        ],
    )
    payload = package.to_dict()

    assert [entry["sequence"] for entry in payload["timeline"]] == [1, 2, 3, 4, 5]
    assert payload["timeline"][0]["title"] == "Qwen Hero gives check"
    highlight_categories = [item["category"] for item in payload["highlights"]]
    assert "check" in highlight_categories
    assert "illegal_move" in highlight_categories
    assert "finish" in highlight_categories
    assert payload["clip_manifest"][0]["start_entry_id"].startswith(("turn:", "event:"))
    assert payload["audio_sync"][0]["start_ms"] == 0
    assert payload["audio_sync"][0]["end_ms"] > payload["audio_sync"][0]["start_ms"]
    assert payload["audio_sync"][1]["start_ms"] > payload["audio_sync"][0]["end_ms"]
    assert payload["audio_sync"][0]["voice_role"] == "narrator"
    assert payload["audio_sync"][2]["voice_role"] == "narrator"
    assert payload["summary"] == {
        "timeline_count": 5,
        "highlight_count": 3,
        "clip_count": 3,
        "audio_cue_count": 5,
        "audio_duration_ms": payload["audio_sync"][-1]["end_ms"],
    }
