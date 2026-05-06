# Rust Engine

This directory is reserved for the future LexiChess Rust engine.

Planned responsibilities:

- board representation and move generation
- search
- evaluation
- style and personality controls
- CPU-first gameplay for low-cost concurrent matches

Current implemented slice:

- a standalone `lexichess-engine` binary
- JSON `health` and `move` commands
- first built-in style profiles:
  - `balanced`
  - `aggressive`
  - `cautious`
  - `trickster`
  - `endgame`
- first Python integration path through the `lexi_engine` provider

Planned non-goals:

- replacing `Stockfish` as the deterministic analysis truth layer
- absorbing the web app or product logic
- duplicating legacy commercial chess engines

Suggested future layout:

```text
rust_engine/
├── Cargo.toml
├── crates/
│   ├── core/
│   ├── eval/
│   ├── personalities/
│   └── ffi/
└── config/
```

The engine should stay original, measurable, and easy to benchmark against the rest of LexiChess.

Quickstart:

```bash
make build-engine
engine/rust_engine/target/release/lexichess-engine health
engine/rust_engine/target/release/lexichess-engine move \
  --fen 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1' \
  --profile balanced \
  --depth 3
```
