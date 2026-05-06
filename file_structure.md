# LexiChess Repository Architecture

This document describes the current repository structure of LexiChess and the architectural direction it is meant to support.

The repository already contains a working backend and early web slice. It now also reserves clear top-level workspaces for future engine and research efforts, so the product can evolve without mixing experimental work directly into the shipping app.

## Design Goals

- Keep the chess runtime independent from any one model family
- Support self-hosted local model runtimes from the start
- Keep the shipping app, the future engine, and the research pipeline in one repository while they are still tightly coupled
- Build the smallest useful product slice before expanding into larger engine and training efforts
- Log enough detail to study move quality, parsing failures, hallucinations, and corrections
- Keep future engine and personality work original, non-infringing, and operationally separate from the web app

## Current And Planned Layout

```text
lexichess/
├── .env.example
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── contracts/
│   └── engine/               # Future app-to-engine integration contracts
├── docs/
│   ├── adr/
│   └── architecture/         # Higher-level architecture notes
├── engine/
│   ├── README.md
│   └── rust_engine/          # Future Rust CPU-first engine workspace
├── Makefile
├── research/
│   ├── datasets/             # Provenance and dataset manifests
│   ├── evaluation/           # Offline research evaluation
│   ├── style_clustering/     # Play-style clustering work
│   └── training/             # Training experiments and configs
├── scripts/
│   └── ...
├── src/
│   └── lexichess/
│       ├── __init__.py
│       ├── cli.py                  # CLI entrypoint for running games
│       ├── config.py               # Environment-driven settings, modes, and profiles
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
│   └── ...                         # Product-facing tests only
├── README.md
├── CONTRIBUTING.md
├── file_structure.md
├── pyproject.toml
└── TASKS.md
```

## Workspace Responsibilities

### `src/lexichess/`

This is the shipping product workspace. It contains the Python app, CLI, web surfaces, data layer, tournaments, ratings, live runtime loop, and current local-model integrations.

### `engine/`

This workspace is reserved for future low-cost engines that should not be tangled into the Python app package.

The initial target is a Rust CPU-first engine that can eventually support:

- cheap concurrent gameplay
- original style profiles
- benchmark anchors
- training partners and personality-backed opponents

### `research/`

This workspace is reserved for experiments that are not yet stable product features.

It should hold:

- corpus provenance
- style clustering experiments
- training runs
- offline evaluation reports

### `contracts/engine/`

This workspace is reserved for the stable boundary between the app and future engine work.

Likely contents:

- request and response schemas
- personality or style profile formats
- reproducibility manifests
- bridge-layer notes for Python-to-Rust integration

## Layer Responsibilities

### `config.py`

Loads environment variables, validates settings, exports safe config snapshots, and chooses the active local runtime without hardcoding that decision in the chess loop.

### `llm/`

Defines the internal contract for local model runtimes. The rest of the application should request a move through this contract and should not care whether the backend is `Ollama`, `vLLM`, or something else running on hardware we control.

### `llm/providers/ollama_provider.py`

Wraps the local HTTP integration for models running through Ollama on the same machine or local network.

### `chess/`

Contains move parsing, validation, and board state handling built around `python-chess`.

### `tournament/`

Coordinates the game loop, asks the active runtimes for moves, and records the results of each turn.

### `cli.py`

Provides the current runnable entrypoint for headless games between configured local backends plus settings inspection.

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

- first engine contract documents under `contracts/engine/`
- first research manifests under `research/datasets/`
- initial style-clustering notebooks or scripts under `research/style_clustering/`
- a Rust engine workspace under `engine/rust_engine/`
- promotion rules for moving research outputs into `src/lexichess/`
