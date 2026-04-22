from pathlib import Path

from lexichess.config import AppSettings, ProviderName


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
