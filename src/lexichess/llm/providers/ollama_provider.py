from __future__ import annotations

import time
from typing import Any

import httpx

from lexichess.llm.base import (
    MoveProvider,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCode,
    ProviderHealthReport,
    RetryPolicy,
    TimeoutPolicy,
)
from lexichess.llm.types import MoveRequest, ProviderResponse, TokenUsage


class OllamaProvider(MoveProvider):
    provider_name = "ollama"

    def __init__(
        self,
        *,
        host: str,
        model: str,
        timeout_seconds: float = 120.0,
        retry_attempts: int = 2,
        retry_base_delay_seconds: float = 0.25,
        api_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        api_base = _normalize_api_base(host)
        self._timeout_policy = TimeoutPolicy(request_timeout_seconds=timeout_seconds)
        self._retry_policy = RetryPolicy(
            max_attempts=max(retry_attempts, 1),
            base_delay_seconds=max(retry_base_delay_seconds, 0.0),
        )
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
        self._client = client or httpx.Client(
            base_url=api_base,
            timeout=timeout_seconds,
            headers=headers,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_sync_requests=True,
            supports_system_instructions=True,
            supports_model_listing=True,
            supports_health_checks=True,
            local_only=True,
        )

    def health_check(self) -> ProviderHealthReport:
        started_at = time.perf_counter()
        try:
            body = self._request_json("tags")
            models = _extract_model_names(body)
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            return ProviderHealthReport(
                provider_name=self.provider_name,
                model=self.model,
                is_healthy=True,
                latency_ms=latency_ms,
                model_available=self.model in models,
                capabilities=self.capabilities(),
                metadata={
                    "host": self.host,
                    "available_models": models,
                    "retry_attempts": self._retry_policy.max_attempts,
                    "request_timeout_seconds": self._timeout_policy.request_timeout_seconds,
                },
            )
        except ProviderError as exc:
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            return ProviderHealthReport(
                provider_name=self.provider_name,
                model=self.model,
                is_healthy=False,
                latency_ms=latency_ms,
                model_available=None,
                error_code=exc.code,
                error_message=str(exc),
                capabilities=self.capabilities(),
                metadata={
                    "host": self.host,
                    "retry_attempts": self._retry_policy.max_attempts,
                    "request_timeout_seconds": self._timeout_policy.request_timeout_seconds,
                },
            )

    def list_models(self) -> tuple[str, ...]:
        body = self._request_json("tags")
        return tuple(_extract_model_names(body))

    def has_model(self, model: str | None = None) -> bool:
        target = model or self.model
        return target in self.list_models()

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
        body = self._request_json("generate", payload=payload)

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        if body.get("error"):
            raise ProviderError(
                str(body["error"]),
                code=ProviderErrorCode.MODEL_UNAVAILABLE,
            )

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

    def _request_json(
        self,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_error: ProviderError | None = None
        for attempt in range(1, self._retry_policy.max_attempts + 1):
            try:
                response = (
                    self._client.post(path, json=payload)
                    if payload is not None
                    else self._client.get(path)
                )
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise ProviderError(
                        "Ollama returned a non-object JSON payload.",
                        code=ProviderErrorCode.INVALID_RESPONSE,
                    )
                return body
            except ProviderError as exc:
                last_error = exc
            except httpx.TimeoutException as exc:
                last_error = ProviderError(
                    f"Ollama request timed out: {exc}",
                    code=ProviderErrorCode.TIMEOUT,
                )
            except httpx.ConnectError as exc:
                last_error = ProviderError(
                    f"Ollama connection failed: {exc}",
                    code=ProviderErrorCode.CONNECTION_ERROR,
                )
            except httpx.HTTPStatusError as exc:
                last_error = ProviderError(
                    f"Ollama HTTP error: {exc}",
                    code=ProviderErrorCode.HTTP_ERROR,
                )
            except httpx.HTTPError as exc:
                last_error = ProviderError(
                    f"Ollama request failed: {exc}",
                    code=ProviderErrorCode.UNKNOWN,
                )
            except ValueError as exc:
                last_error = ProviderError(
                    f"Ollama returned invalid JSON: {exc}",
                    code=ProviderErrorCode.INVALID_RESPONSE,
                )

            if attempt < self._retry_policy.max_attempts:
                time.sleep(self._retry_policy.base_delay_seconds * attempt)

        if last_error is None:
            raise ProviderError(
                "Ollama request failed.", code=ProviderErrorCode.UNKNOWN
            )
        raise last_error


def _normalize_api_base(host: str) -> str:
    base = host.rstrip("/")
    if base.endswith("/api"):
        return base
    return f"{base}/api"


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _extract_model_names(payload: dict[str, Any]) -> list[str]:
    models = payload.get("models", [])
    extracted: list[str] = []
    if not isinstance(models, list):
        return extracted
    for model in models:
        if isinstance(model, dict):
            name = model.get("name")
            if isinstance(name, str):
                extracted.append(name)
    return extracted
