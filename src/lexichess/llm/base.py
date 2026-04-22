from __future__ import annotations

from abc import ABC, abstractmethod

from lexichess.llm.types import MoveRequest, ProviderResponse


class ProviderError(RuntimeError):
    """Raised when a model backend fails to produce a usable response."""


class MoveProvider(ABC):
    provider_name: str
    model: str

    @abstractmethod
    def request_move(self, request: MoveRequest) -> ProviderResponse:
        raise NotImplementedError
