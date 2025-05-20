from __future__ import annotations

from abc import ABC, abstractmethod
import chess


class BaseLLM(ABC):
    """Abstract base class for LLM interfaces."""

    @abstractmethod
    def generate_move(self, board: chess.Board, history: str) -> str:
        """Generate the next move in UCI format."""

    def record_conversation(self, text: str) -> None:
        """Hook for recording conversation if desired."""
        pass
