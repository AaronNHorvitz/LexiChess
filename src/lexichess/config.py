from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv


class ProviderName(str, Enum):
    OLLAMA = "ollama"


@dataclass(frozen=True, slots=True)
class OllamaSettings:
    host: str = "http://localhost:11434"
    model: str = "qwen3:8b"
    timeout_seconds: float = 120.0
    api_key: str | None = None


@dataclass(frozen=True, slots=True)
class AppSettings:
    default_provider: ProviderName
    database_path: Path
    max_plies: int
    move_temperature: float
    max_output_tokens: int
    log_raw_response_json: bool
    ollama: OllamaSettings

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        dotenv_path: str | Path | None = ".env",
    ) -> "AppSettings":
        if dotenv_path is not None:
            load_dotenv(dotenv_path, override=False)

        raw = dict(os.environ if env is None else env)
        default_provider = ProviderName(
            raw.get("LEXICHESS_PROVIDER", ProviderName.OLLAMA).strip().lower()
        )
        model_override = _optional_str(raw.get("LEXICHESS_MODEL"))

        return cls(
            default_provider=default_provider,
            database_path=Path(raw.get("LEXICHESS_DB_PATH", "lexichess.db")),
            max_plies=_parse_int(raw.get("LEXICHESS_MAX_PLIES"), 200),
            move_temperature=_parse_float(raw.get("LEXICHESS_TEMPERATURE"), 0.2),
            max_output_tokens=_parse_int(raw.get("LEXICHESS_MAX_OUTPUT_TOKENS"), 64),
            log_raw_response_json=_parse_bool(
                raw.get("LEXICHESS_LOG_RAW_RESPONSE_JSON"), True
            ),
            ollama=OllamaSettings(
                host=raw.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/"),
                model=model_override
                or _optional_str(raw.get("OLLAMA_MODEL"))
                or "qwen3:8b",
                timeout_seconds=_parse_float(raw.get("OLLAMA_TIMEOUT_SECONDS"), 120.0),
                api_key=_optional_str(raw.get("OLLAMA_API_KEY")),
            ),
        )

    def model_for(self, provider: ProviderName | str) -> str:
        provider_name = ProviderName(str(provider).lower())
        if provider_name is ProviderName.OLLAMA:
            return self.ollama.model
        raise ValueError(f"Unsupported provider: {provider}")


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Unable to parse boolean value: {value!r}")


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _parse_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    return float(value)
