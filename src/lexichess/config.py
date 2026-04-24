from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from dotenv import load_dotenv


class ProviderName(str, Enum):
    OLLAMA = "ollama"
    STOCKFISH = "stockfish"


class EnvironmentProfile(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class GameMode(str, Enum):
    BENCHMARK = "benchmark"
    SHOWMATCH = "showmatch"
    INTERACTIVE = "interactive"


class SeatController(str, Enum):
    HUMAN = "human"
    MODEL = "model"


class PersonaRole(str, Enum):
    PLAYER = "player"
    REFEREE = "referee"
    COACH = "coach"
    ANNOUNCER = "announcer"


@dataclass(frozen=True, slots=True)
class OllamaSettings:
    host: str = "http://localhost:11434"
    model: str = "qwen3:8b"
    timeout_seconds: float = 120.0
    retry_attempts: int = 2
    retry_base_delay_seconds: float = 0.25
    api_key: str | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkModeSettings:
    allow_banter: bool = False
    allow_human_handoffs: bool = False


@dataclass(frozen=True, slots=True)
class ShowmatchModeSettings:
    allow_banter: bool = True
    require_referee: bool = True


@dataclass(frozen=True, slots=True)
class InteractiveModeSettings:
    allow_human_takeover: bool = True
    allow_llm_takeover: bool = True


@dataclass(frozen=True, slots=True)
class CharacterModeSettings:
    enable_voices: bool = False
    enable_avatars: bool = False
    enable_memory: bool = False


@dataclass(frozen=True, slots=True)
class RefereeSettings:
    enabled: bool = True
    provider: ProviderName = ProviderName.OLLAMA
    model: str = "gemma4:latest"
    speaker_name: str = "Gemma 4 Referee"
    temperature: float = 0.4
    max_output_tokens: int = 96
    allow_fallback: bool = True


@dataclass(frozen=True, slots=True)
class BanterSettings:
    enabled: bool = True
    provider: ProviderName = ProviderName.OLLAMA
    model: str = "qwen3:8b"
    temperature: float = 0.9
    max_output_tokens: int = 72
    allow_fallback: bool = True


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    level: str = "INFO"
    json: bool = False
    redact_secrets: bool = True


@dataclass(frozen=True, slots=True)
class StockfishSettings:
    profile: str = "stockfish_expert"
    path: str = "stockfish"
    depth: int = 12
    multipv: int = 3
    movetime_ms: int | None = None


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    enabled: frozenset[str]

    def is_enabled(self, name: str) -> bool:
        return name in self.enabled


@dataclass(frozen=True, slots=True)
class AppSettings:
    environment_profile: EnvironmentProfile
    default_provider: ProviderName
    default_game_mode: GameMode
    default_seat_controller: SeatController
    default_persona_role: PersonaRole
    database_path: Path
    max_plies: int
    move_temperature: float
    max_output_tokens: int
    log_raw_response_json: bool
    feature_flags: FeatureFlags
    logging: LoggingSettings
    benchmark_mode: BenchmarkModeSettings
    showmatch_mode: ShowmatchModeSettings
    interactive_mode: InteractiveModeSettings
    character_mode: CharacterModeSettings
    referee: RefereeSettings
    banter: BanterSettings
    ollama: OllamaSettings
    stockfish: StockfishSettings

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
            environment_profile=EnvironmentProfile(
                raw.get("LEXICHESS_ENV_PROFILE", EnvironmentProfile.DEV).strip().lower()
            ),
            default_provider=default_provider,
            default_game_mode=GameMode(
                raw.get("LEXICHESS_DEFAULT_GAME_MODE", GameMode.BENCHMARK)
                .strip()
                .lower()
            ),
            default_seat_controller=SeatController(
                raw.get("LEXICHESS_DEFAULT_SEAT_CONTROLLER", SeatController.MODEL)
                .strip()
                .lower()
            ),
            default_persona_role=PersonaRole(
                raw.get("LEXICHESS_DEFAULT_PERSONA_ROLE", PersonaRole.REFEREE)
                .strip()
                .lower()
            ),
            database_path=Path(raw.get("LEXICHESS_DB_PATH", "lexichess.db")),
            max_plies=_parse_int(raw.get("LEXICHESS_MAX_PLIES"), 200),
            move_temperature=_parse_float(raw.get("LEXICHESS_TEMPERATURE"), 0.2),
            max_output_tokens=_parse_int(raw.get("LEXICHESS_MAX_OUTPUT_TOKENS"), 64),
            log_raw_response_json=_parse_bool(
                raw.get("LEXICHESS_LOG_RAW_RESPONSE_JSON"), True
            ),
            feature_flags=FeatureFlags(
                enabled=frozenset(
                    _parse_csv(raw.get("LEXICHESS_FEATURE_FLAGS", "settings-export"))
                )
            ),
            logging=LoggingSettings(
                level=raw.get("LEXICHESS_LOG_LEVEL", "INFO").strip().upper(),
                json=_parse_bool(raw.get("LEXICHESS_LOG_FORMAT_JSON"), False),
                redact_secrets=_parse_bool(raw.get("LEXICHESS_REDACT_SECRETS"), True),
            ),
            benchmark_mode=BenchmarkModeSettings(
                allow_banter=_parse_bool(
                    raw.get("LEXICHESS_BENCHMARK_ALLOW_BANTER"), False
                ),
                allow_human_handoffs=_parse_bool(
                    raw.get("LEXICHESS_BENCHMARK_ALLOW_HUMAN_HANDOFFS"), False
                ),
            ),
            showmatch_mode=ShowmatchModeSettings(
                allow_banter=_parse_bool(
                    raw.get("LEXICHESS_SHOWMATCH_ALLOW_BANTER"), True
                ),
                require_referee=_parse_bool(
                    raw.get("LEXICHESS_SHOWMATCH_REQUIRE_REFEREE"), True
                ),
            ),
            interactive_mode=InteractiveModeSettings(
                allow_human_takeover=_parse_bool(
                    raw.get("LEXICHESS_INTERACTIVE_ALLOW_HUMAN_TAKEOVER"), True
                ),
                allow_llm_takeover=_parse_bool(
                    raw.get("LEXICHESS_INTERACTIVE_ALLOW_LLM_TAKEOVER"), True
                ),
            ),
            character_mode=CharacterModeSettings(
                enable_voices=_parse_bool(
                    raw.get("LEXICHESS_CHARACTER_ENABLE_VOICES"), False
                ),
                enable_avatars=_parse_bool(
                    raw.get("LEXICHESS_CHARACTER_ENABLE_AVATARS"), False
                ),
                enable_memory=_parse_bool(
                    raw.get("LEXICHESS_CHARACTER_ENABLE_MEMORY"), False
                ),
            ),
            referee=RefereeSettings(
                enabled=_parse_bool(raw.get("LEXICHESS_REFEREE_ENABLED"), True),
                provider=ProviderName(
                    raw.get("LEXICHESS_REFEREE_PROVIDER", ProviderName.OLLAMA)
                    .strip()
                    .lower()
                ),
                model=_optional_str(raw.get("LEXICHESS_REFEREE_MODEL"))
                or "gemma4:latest",
                speaker_name=raw.get(
                    "LEXICHESS_REFEREE_SPEAKER_NAME",
                    "Gemma 4 Referee",
                ).strip(),
                temperature=_parse_float(
                    raw.get("LEXICHESS_REFEREE_TEMPERATURE"),
                    0.4,
                ),
                max_output_tokens=_parse_int(
                    raw.get("LEXICHESS_REFEREE_MAX_OUTPUT_TOKENS"),
                    96,
                ),
                allow_fallback=_parse_bool(
                    raw.get("LEXICHESS_REFEREE_ALLOW_FALLBACK"),
                    True,
                ),
            ),
            banter=BanterSettings(
                enabled=_parse_bool(raw.get("LEXICHESS_BANTER_ENABLED"), True),
                provider=ProviderName(
                    raw.get("LEXICHESS_BANTER_PROVIDER", ProviderName.OLLAMA)
                    .strip()
                    .lower()
                ),
                model=_optional_str(raw.get("LEXICHESS_BANTER_MODEL"))
                or model_override
                or _optional_str(raw.get("OLLAMA_MODEL"))
                or "qwen3:8b",
                temperature=_parse_float(
                    raw.get("LEXICHESS_BANTER_TEMPERATURE"),
                    0.9,
                ),
                max_output_tokens=_parse_int(
                    raw.get("LEXICHESS_BANTER_MAX_OUTPUT_TOKENS"),
                    72,
                ),
                allow_fallback=_parse_bool(
                    raw.get("LEXICHESS_BANTER_ALLOW_FALLBACK"),
                    True,
                ),
            ),
            ollama=OllamaSettings(
                host=raw.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/"),
                model=model_override
                or _optional_str(raw.get("OLLAMA_MODEL"))
                or "qwen3:8b",
                timeout_seconds=_parse_float(raw.get("OLLAMA_TIMEOUT_SECONDS"), 120.0),
                retry_attempts=_parse_int(raw.get("OLLAMA_RETRY_ATTEMPTS"), 2),
                retry_base_delay_seconds=_parse_float(
                    raw.get("OLLAMA_RETRY_BASE_DELAY_SECONDS"),
                    0.25,
                ),
                api_key=_optional_str(raw.get("OLLAMA_API_KEY")),
            ),
            stockfish=StockfishSettings(
                profile=raw.get("STOCKFISH_PROFILE", "stockfish_expert").strip(),
                path=raw.get("STOCKFISH_PATH", "stockfish").strip(),
                depth=_parse_int(raw.get("STOCKFISH_DEPTH"), 12),
                multipv=_parse_int(raw.get("STOCKFISH_MULTIPV"), 3),
                movetime_ms=_parse_optional_int(raw.get("STOCKFISH_MOVETIME_MS")),
            ),
        )

    def model_for(self, provider: ProviderName | str) -> str:
        provider_name = ProviderName(str(provider).lower())
        if provider_name is ProviderName.OLLAMA:
            return self.ollama.model
        if provider_name is ProviderName.STOCKFISH:
            return self.stockfish.profile
        raise ValueError(f"Unsupported provider: {provider}")

    def to_dict(self, *, redact_secrets: bool | None = None) -> dict[str, Any]:
        redact = (
            self.logging.redact_secrets if redact_secrets is None else redact_secrets
        )

        return {
            "environment_profile": self.environment_profile.value,
            "default_provider": self.default_provider.value,
            "default_game_mode": self.default_game_mode.value,
            "default_seat_controller": self.default_seat_controller.value,
            "default_persona_role": self.default_persona_role.value,
            "database_path": str(self.database_path),
            "max_plies": self.max_plies,
            "move_temperature": self.move_temperature,
            "max_output_tokens": self.max_output_tokens,
            "log_raw_response_json": self.log_raw_response_json,
            "feature_flags": sorted(self.feature_flags.enabled),
            "logging": {
                "level": self.logging.level,
                "json": self.logging.json,
                "redact_secrets": self.logging.redact_secrets,
            },
            "benchmark_mode": {
                "allow_banter": self.benchmark_mode.allow_banter,
                "allow_human_handoffs": self.benchmark_mode.allow_human_handoffs,
            },
            "showmatch_mode": {
                "allow_banter": self.showmatch_mode.allow_banter,
                "require_referee": self.showmatch_mode.require_referee,
            },
            "interactive_mode": {
                "allow_human_takeover": self.interactive_mode.allow_human_takeover,
                "allow_llm_takeover": self.interactive_mode.allow_llm_takeover,
            },
            "character_mode": {
                "enable_voices": self.character_mode.enable_voices,
                "enable_avatars": self.character_mode.enable_avatars,
                "enable_memory": self.character_mode.enable_memory,
            },
            "referee": {
                "enabled": self.referee.enabled,
                "provider": self.referee.provider.value,
                "model": self.referee.model,
                "speaker_name": self.referee.speaker_name,
                "temperature": self.referee.temperature,
                "max_output_tokens": self.referee.max_output_tokens,
                "allow_fallback": self.referee.allow_fallback,
            },
            "banter": {
                "enabled": self.banter.enabled,
                "provider": self.banter.provider.value,
                "model": self.banter.model,
                "temperature": self.banter.temperature,
                "max_output_tokens": self.banter.max_output_tokens,
                "allow_fallback": self.banter.allow_fallback,
            },
            "ollama": {
                "host": self.ollama.host,
                "model": self.ollama.model,
                "timeout_seconds": self.ollama.timeout_seconds,
                "retry_attempts": self.ollama.retry_attempts,
                "retry_base_delay_seconds": self.ollama.retry_base_delay_seconds,
                "api_key": _redacted_value(self.ollama.api_key, redact=redact),
            },
            "stockfish": {
                "profile": self.stockfish.profile,
                "path": self.stockfish.path,
                "depth": self.stockfish.depth,
                "multipv": self.stockfish.multipv,
                "movetime_ms": self.stockfish.movetime_ms,
            },
        }


def _redacted_value(value: str | None, *, redact: bool) -> str | None:
    if value is None:
        return None
    return "***REDACTED***" if redact else value


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


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return int(stripped)


def _parse_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    return float(value)
