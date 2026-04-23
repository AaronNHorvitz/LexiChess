from __future__ import annotations

import json

import httpx
import pytest

from lexichess.llm.base import ProviderError, ProviderErrorCode
from lexichess.llm.providers import OllamaProvider
from lexichess.llm.types import MoveRequest


def test_ollama_provider_hits_generate_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert request.url.path == "/api/generate"
        assert payload["model"] == "llama3.2"
        assert payload["stream"] is False
        return httpx.Response(
            200,
            json={
                "model": "llama3.2",
                "response": "e4",
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 14,
                "eval_count": 1,
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://localhost:11434/api",
    )
    provider = OllamaProvider(
        host="http://localhost:11434",
        model="llama3.2",
        client=client,
    )

    request = MoveRequest(
        game_id=1,
        move_number=1,
        color="white",
        fen="startpos",
        prompt="Choose a legal move.",
        instructions="Return one SAN move.",
        legal_moves=("e4", "d4"),
        temperature=0.2,
        max_output_tokens=32,
    )
    response = provider.request_move(request)

    assert response.output_text == "e4"
    assert response.finish_reason == "stop"
    assert response.usage.total_tokens == 15


def test_ollama_provider_health_check_lists_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"
        return httpx.Response(
            200,
            json={"models": [{"name": "llama3.2"}, {"name": "qwen3:8b"}]},
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://localhost:11434/api",
    )
    provider = OllamaProvider(
        host="http://localhost:11434",
        model="qwen3:8b",
        client=client,
    )

    report = provider.health_check()

    assert report.is_healthy is True
    assert report.model_available is True
    assert "qwen3:8b" in report.metadata["available_models"]


def test_ollama_provider_surfaces_error_payloads() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "model unavailable"})

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://localhost:11434/api",
    )
    provider = OllamaProvider(
        host="http://localhost:11434",
        model="llama3.2",
        client=client,
    )

    request = MoveRequest(
        game_id=None,
        move_number=1,
        color="white",
        fen="startpos",
        prompt="Choose a legal move.",
        instructions="Return one SAN move.",
        legal_moves=("e4",),
    )

    with pytest.raises(ProviderError, match="model unavailable"):
        provider.request_move(request)


def test_ollama_provider_categorizes_connection_failures() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "no route", request=httpx.Request("GET", "http://test")
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://localhost:11434/api",
    )
    provider = OllamaProvider(
        host="http://localhost:11434",
        model="llama3.2",
        client=client,
    )

    report = provider.health_check()

    assert report.is_healthy is False
    assert report.error_code is ProviderErrorCode.CONNECTION_ERROR
