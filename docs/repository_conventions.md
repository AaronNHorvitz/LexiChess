# Repository Conventions

These conventions keep the LexiChess repository predictable as it grows.

## Top-Level Naming

- `README.md` explains what the project is and what currently exists.
- `PRD.md` captures the product requirements and long-range product shape.
- `TASKS.md` is the execution backlog.
- `CONTRIBUTING.md` is the contributor quickstart.
- `file_structure.md` documents the planned and current architecture.

## Code Layout

- `src/lexichess/` contains application code.
- `tests/` contains automated tests.
- `scripts/` contains local developer and operational helper scripts.
- `docs/` contains policies, conventions, and reference docs that support the repo.

## Naming Rules

- Python modules use `snake_case`.
- Public classes use `PascalCase`.
- Environment variables use `UPPER_SNAKE_CASE`.
- Markdown docs use descriptive lowercase filenames except for root-level canonical docs that are intentionally uppercase.

## Documentation Rules

- Root docs should stay high-signal and product-facing.
- Implementation and policy details belong under `docs/`.
- When repo structure changes, update both `README.md` and any architecture notes that describe it.
