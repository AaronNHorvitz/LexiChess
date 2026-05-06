# Engine Workspace

This directory is reserved for low-cost, non-LLM chess engines that support the LexiChess product.

The current plan is to keep the production web app in `src/lexichess/` while building a separate engine workspace here for:

- a future Rust CPU-first chess engine
- engine personality systems
- engine evaluation and benchmarking tools
- integration adapters that let LexiChess use the engine without coupling app code to engine internals

Why this lives in the same repository:

- the app, benchmark pipeline, and future engine will share contracts
- cross-cutting work is easier while the architecture is still changing quickly
- we can keep one product roadmap while still separating concerns cleanly

Near-term intent:

- keep this workspace documentation-first until the engine design is stable
- avoid mixing Rust engine code into `src/lexichess/`
- treat the engine as an original LexiChess subsystem, not a recreation of any legacy commercial engine
