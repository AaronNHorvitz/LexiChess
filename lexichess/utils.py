from __future__ import annotations
import datetime


def now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.datetime.utcnow().isoformat()
