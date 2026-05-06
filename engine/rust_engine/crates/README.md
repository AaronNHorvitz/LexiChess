# Planned Crates

This directory is reserved for Rust crates once the engine workspace is implemented.

Likely crate split:

- `core`: board state, move generation, search loop
- `eval`: evaluation functions and learned evaluators
- `personalities`: style profiles and personality parameterization
- `ffi`: bindings or bridge layer for the Python app
