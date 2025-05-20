from __future__ import annotations

from transformers import pipeline
import chess

from .base import BaseLLM


class HuggingFaceLLM(BaseLLM):
    """LLM interface using HuggingFace transformers models."""

    def __init__(self, model_name: str = "gpt2", **generate_kwargs) -> None:
        self.generator = pipeline("text-generation", model=model_name)
        self.generate_kwargs = generate_kwargs
        self.history = []

    def generate_move(self, board: chess.Board, history: str) -> str:
        prompt = f"Board FEN: {board.fen()}\nHistory: {history}\nMove:"
        result = self.generator(prompt, max_new_tokens=5, **self.generate_kwargs)[0][
            "generated_text"
        ]
        # naive parsing: get first token after prompt
        move = result[len(prompt) :].split()[0]
        self.history.append((prompt, move))
        return move

    def record_conversation(self, text: str) -> None:
        self.history.append(("conversation", text))
