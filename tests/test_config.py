from pathlib import Path

from lexichess.config import (
    AppSettings,
    EnvironmentProfile,
    GameMode,
    PersonaRole,
    ProviderName,
    SeatController,
)


def test_settings_load_defaults_without_touching_real_env(tmp_path: Path) -> None:
    database_path = tmp_path / "lexichess.db"
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_PROVIDER": "ollama",
            "LEXICHESS_DB_PATH": str(database_path),
            "OLLAMA_MODEL": "llama3.2",
        },
        dotenv_path=None,
    )

    assert settings.default_provider is ProviderName.OLLAMA
    assert settings.database_path == database_path
    assert settings.model_for("ollama") == "llama3.2"


def test_global_model_override_applies_to_local_runtime() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_MODEL": "custom-model",
        },
        dotenv_path=None,
    )

    assert settings.ollama.model == "custom-model"


def test_settings_parse_profiles_modes_and_flags() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_ENV_PROFILE": "prod",
            "LEXICHESS_DEFAULT_GAME_MODE": "interactive",
            "LEXICHESS_DEFAULT_SEAT_CONTROLLER": "human",
            "LEXICHESS_DEFAULT_PERSONA_ROLE": "coach",
            "LEXICHESS_FEATURE_FLAGS": "settings-export,voice-preview",
            "LEXICHESS_CHARACTER_ENABLE_VOICES": "true",
            "LEXICHESS_LOG_FORMAT_JSON": "true",
        },
        dotenv_path=None,
    )

    assert settings.environment_profile is EnvironmentProfile.PROD
    assert settings.default_game_mode is GameMode.INTERACTIVE
    assert settings.default_seat_controller is SeatController.HUMAN
    assert settings.default_persona_role is PersonaRole.COACH
    assert settings.feature_flags.is_enabled("voice-preview")
    assert settings.character_mode.enable_voices is True
    assert settings.logging.json is True


def test_settings_export_redacts_secrets_by_default() -> None:
    settings = AppSettings.from_env(
        env={
            "OLLAMA_API_KEY": "top-secret",
        },
        dotenv_path=None,
    )

    payload = settings.to_dict()

    assert payload["ollama"]["api_key"] == "***REDACTED***"


def test_settings_include_runtime_retry_and_stockfish_configuration() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_PROVIDER": "stockfish",
            "OLLAMA_RETRY_ATTEMPTS": "3",
            "OLLAMA_RETRY_BASE_DELAY_SECONDS": "0.5",
            "STOCKFISH_PROFILE": "stockfish_club",
            "STOCKFISH_PATH": "/usr/bin/stockfish",
            "STOCKFISH_DEPTH": "14",
            "STOCKFISH_MULTIPV": "4",
            "STOCKFISH_MOVETIME_MS": "750",
        },
        dotenv_path=None,
    )

    assert settings.ollama.retry_attempts == 3
    assert settings.ollama.retry_base_delay_seconds == 0.5
    assert settings.default_provider is ProviderName.STOCKFISH
    assert settings.stockfish.profile == "stockfish_club"
    assert settings.model_for("stockfish") == "stockfish_club"
    assert settings.stockfish.path == "/usr/bin/stockfish"
    assert settings.stockfish.depth == 14
    assert settings.stockfish.multipv == 4
    assert settings.stockfish.movetime_ms == 750
