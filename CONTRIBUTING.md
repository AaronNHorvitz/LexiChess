# Contributing to LexiChess

Thanks for your interest in LexiChess.

LexiChess now has a working MVP backend slice, so the most useful contributions right now are focused improvements to the runtime, local model layer, storage, and evaluation flow.

## Current State

The repository contains a CLI-driven game runner, a local-model adapter for `Ollama`, SQLite logging, and tests. Before opening large pull requests, please align with the MVP scope described in [README.md](./README.md) and the architecture notes in [file_structure.md](./file_structure.md).

## Local Setup

1. Install Python 3.10 or newer.
2. Create a virtual environment: `python -m venv .venv`
3. Install the current dependency set:

```bash
.venv/bin/python -m pip install python-chess httpx python-dotenv pytest ruff black
```

4. Run the test suite:

```bash
PYTHONPATH=src .venv/bin/pytest
```

There is no web UI yet. The current entrypoint is [src/lexichess/cli.py](/var/home/aaronnhorvitz/dev/LexiChess/src/lexichess/cli.py:1).

## High-Value Contribution Areas

- Tighten the MVP architecture and documentation
- Improve move prompts and response parsing
- Add tournament orchestration on top of the single-game runner
- Improve SQLite persistence and replay tooling
- Expand local runtime coverage beyond `Ollama`
- Add tests for edge cases and evaluation scenarios

## Working Principles

- Keep the MVP centered on tournament orchestration, move validation, and logging
- Preserve a runtime-agnostic design so multiple self-hosted backends can share the same match loop
- Prefer small, focused pull requests over broad speculative scaffolding
- Update documentation whenever the repository structure or setup expectations change

## Pull Requests

When you open a pull request:

- Explain what changed and why
- Note how you verified the change
- Add or update tests if code was introduced or behavior changed
- Keep the README and architecture notes aligned with the new state of the repo

For documentation-only changes, a clear manual review is enough.

## Questions

If something about the MVP boundary or local runtime strategy is unclear, start by checking [README.md](./README.md), [file_structure.md](./file_structure.md), and [TASKS.md](./TASKS.md). If the docs still leave open questions, raise them before building large features.
