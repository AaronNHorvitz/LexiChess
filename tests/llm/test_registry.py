import pytest

from lexichess.config import AppSettings
from lexichess.llm.providers import OllamaProvider
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
