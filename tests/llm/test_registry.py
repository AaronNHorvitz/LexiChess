import pytest

from lexichess.config import AppSettings
from lexichess.llm.providers import (
    LexiEngineProvider,
    OllamaProvider,
    StockfishMoveProvider,
)
from lexichess.llm.registry import build_provider


def test_registry_builds_ollama_provider_with_override() -> None:
    settings = AppSettings.from_env(env={}, dotenv_path=None)

    provider = build_provider("ollama", settings, model="llama3.2")

    assert isinstance(provider, OllamaProvider)
    assert provider.model == "llama3.2"
    assert provider.capabilities().supports_health_checks is True


def test_registry_rejects_unknown_provider() -> None:
    settings = AppSettings.from_env(env={}, dotenv_path=None)

    with pytest.raises(ValueError, match="Unsupported provider"):
        build_provider("vllm", settings)


def test_registry_builds_stockfish_provider() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_PROVIDER": "stockfish",
            "STOCKFISH_PROFILE": "stockfish_club",
        },
        dotenv_path=None,
    )

    provider = build_provider("stockfish", settings)

    assert isinstance(provider, StockfishMoveProvider)
    assert provider.model == "stockfish_club"


def test_registry_builds_lexi_engine_provider() -> None:
    settings = AppSettings.from_env(
        env={
            "LEXICHESS_PROVIDER": "lexi_engine",
            "LEXI_ENGINE_PROFILE": "aggressive",
            "LEXI_ENGINE_DEPTH": "4",
        },
        dotenv_path=None,
    )

    provider = build_provider("lexi_engine", settings)

    assert isinstance(provider, LexiEngineProvider)
    assert provider.model == "aggressive"
    assert provider.depth == 4
