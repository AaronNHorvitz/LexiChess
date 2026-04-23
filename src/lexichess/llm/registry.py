from __future__ import annotations

from lexichess.config import AppSettings, ProviderName
from lexichess.llm.base import MoveProvider
from lexichess.llm.providers import OllamaProvider


def build_provider(
    provider_name: ProviderName | str,
    settings: AppSettings,
    *,
    model: str | None = None,
) -> MoveProvider:
    try:
        normalized_name = ProviderName(str(provider_name).lower())
    except ValueError as exc:
        raise ValueError(f"Unsupported provider: {provider_name}") from exc

    if normalized_name is ProviderName.OLLAMA:
        return OllamaProvider(
            host=settings.ollama.host,
            model=model or settings.ollama.model,
            timeout_seconds=settings.ollama.timeout_seconds,
            retry_attempts=settings.ollama.retry_attempts,
            retry_base_delay_seconds=settings.ollama.retry_base_delay_seconds,
            api_key=settings.ollama.api_key,
        )

    raise ValueError(f"Unsupported provider: {provider_name}")
