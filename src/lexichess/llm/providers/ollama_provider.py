from __future__ import annotations

import time
from typing import Any

import httpx

from lexichess.llm.base import MoveProvider, ProviderError
from lexichess.llm.types import MoveRequest, ProviderResponse, TokenUsage


class OllamaProvider(MoveProvider):
    provider_name = "ollama"

    def __init__(
        self,
        *,
        host: str,
        model: str,
        timeout_seconds: float = 120.0,
        api_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        api_base = _normalize_api_base(host)
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
        self._client = client or httpx.Client(
            base_url=api_base,
            timeout=timeout_seconds,
            headers=headers,
        )

    def request_move(self, request: MoveRequest) -> ProviderResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": request.prompt,
            "system": request.instructions,
            "stream": False,
        }
        options: dict[str, Any] = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            options["num_predict"] = request.max_output_tokens
        if options:
            payload["options"] = options

        started_at = time.perf_counter()
        try:
            response = self._client.post("generate", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Ollama request failed: {exc}") from exc

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        body = response.json()
        if body.get("error"):
            raise ProviderError(str(body["error"]))

        input_tokens = _coerce_int(body.get("prompt_eval_count"))
        output_tokens = _coerce_int(body.get("eval_count"))
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens

        return ProviderResponse(
            provider=self.provider_name,
            model=self.model,
            output_text=str(body.get("response", "")).strip(),
            raw_response=body,
            latency_ms=latency_ms,
            usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
            finish_reason=body.get("done_reason"),
        )


def _normalize_api_base(host: str) -> str:
    base = host.rstrip("/")
    if base.endswith("/api"):
        return base
    return f"{base}/api"


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
