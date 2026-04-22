# LexiChess MVP Architecture

This document describes the current MVP structure of LexiChess and the architectural direction it is meant to support.

The repository now contains a working backend slice for running and logging games, while still leaving larger product features like tournaments, UI, commentary, and tutoring for later phases.

## Design Goals

- Keep the chess runtime independent from any one model family
- Support self-hosted local model runtimes from the start
- Build the smallest useful MVP before expanding into spectator experiences and broader product features
- Log enough detail to study move quality, parsing failures, hallucinations, and corrections

## Current Layout

```text
lexichess/
├── .env.example
├── src/
│   └── lexichess/
│       ├── __init__.py
│       ├── cli.py                  # CLI entrypoint for running games
│       ├── config.py               # Environment-driven settings and runtime selection
│       ├── chess/
│       │   ├── __init__.py
│       │   ├── board.py            # Board wrapper and legal move validation
│       │   └── parsing.py          # SAN/UCI extraction and move parsing helpers
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py             # Runtime interface used by the tournament loop
│       │   ├── registry.py         # Runtime lookup and initialization
│       │   ├── types.py            # Shared request and response models
│       │   └── providers/
│       │       ├── __init__.py
│       │       └── ollama_provider.py
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── schema.py           # SQLite schema for games, turns, and hallucinations
│       │   └── repository.py       # Read and write helpers
│       └── tournament/
│           ├── __init__.py
│           ├── models.py           # Game and turn domain models
│           └── runner.py           # Match loop orchestration
├── tests/
│   ├── chess/
│   ├── llm/
│   ├── storage/
│   └── tournament/
├── README.md
├── CONTRIBUTING.md
├── file_structure.md
├── pyproject.toml
└── TASKS.md
```

## Layer Responsibilities

### `config.py`

Loads environment variables, validates settings, and chooses the active local runtime without hardcoding that decision in the chess loop.

### `llm/`

Defines the internal contract for local model runtimes. The rest of the application should request a move through this contract and should not care whether the backend is `Ollama`, `vLLM`, or something else running on hardware we control.

### `llm/providers/ollama_provider.py`

Wraps the local HTTP integration for models running through Ollama on the same machine or local network.

### `chess/`

Contains move parsing, validation, and board state handling built around `python-chess`.

### `tournament/`

Coordinates the game loop, asks the active runtimes for moves, and records the results of each turn.

### `cli.py`

Provides the current runnable entrypoint for headless games between configured local backends.

### `storage/`

Stores enough structured data to replay games and inspect model behavior:

- runtime name
- model name
- prompt sent to the model
- raw model response
- parsed move
- legality result
- latency and error metadata
- hallucination classification

## Runtime Notes

The intended architecture is local-runtime-based:

- `Ollama` is the initial local backend for running models on hardware such as an RTX 4090
- `vLLM` can be added later without changing tournament logic if higher-throughput local serving becomes useful
- `llama.cpp` can be added later for GGUF-heavy single-node and edge workflows

This separation matters because local runtimes expose different protocols, batching behavior, and hardware tradeoffs. LexiChess should expose one internal runtime contract and let each adapter translate to the backend-specific wire format.

## Near-Term Expansion

The next structural additions will likely be:

- richer tournament orchestration
- replay and export utilities
- self-hosted runtime expansion beyond Ollama
- Stockfish-backed analysis services
- a web-facing spectator layer
