from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lexichess.llm.types import MoveRequest, ProviderResponse


class ProviderErrorCode(str, Enum):
    UNKNOWN = "unknown"
    CONNECTION_ERROR = "connection_error"
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_RESPONSE = "invalid_response"


class ProviderError(RuntimeError):
    """Raised when a model backend fails to produce a usable response."""

    def __init__(
        self,
        message: str,
        *,
        code: ProviderErrorCode = ProviderErrorCode.UNKNOWN,
    ) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    supports_sync_requests: bool = True
    supports_system_instructions: bool = True
    supports_model_listing: bool = False
    supports_health_checks: bool = False
    local_only: bool = True


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 2
    base_delay_seconds: float = 0.25


@dataclass(frozen=True, slots=True)
class TimeoutPolicy:
    request_timeout_seconds: float


@dataclass(frozen=True, slots=True)
class ProviderHealthReport:
    provider_name: str
    model: str | None
    is_healthy: bool
    latency_ms: int | None = None
    model_available: bool | None = None
    error_code: ProviderErrorCode | None = None
    error_message: str | None = None
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    metadata: dict[str, Any] = field(default_factory=dict)


class MoveProvider(ABC):
    provider_name: str
    model: str

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> ProviderHealthReport:
        raise NotImplementedError

    @abstractmethod
    def request_move(self, request: MoveRequest) -> ProviderResponse:
        raise NotImplementedError
