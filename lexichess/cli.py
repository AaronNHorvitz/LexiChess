from __future__ import annotations

import argparse

from .llm.huggingface import HuggingFaceLLM
from .game import LexiChessGame


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a LexiChess match between two HuggingFace models"
    )
    parser.add_argument(
        "--white-model", default="gpt2", help="Model name for the white player"
    )
    parser.add_argument(
        "--black-model", default="gpt2", help="Model name for the black player"
    )
    args = parser.parse_args()

    white = HuggingFaceLLM(model_name=args.white_model)
    black = HuggingFaceLLM(model_name=args.black_model)
    game = LexiChessGame(white, black)
    result = game.play()
    print("Game result:", result)


if __name__ == "__main__":
    main()
