# LexiChess Sprint Master Checklist

This checklist is the ordered sprint plan for taking LexiChess from the current backend MVP to the full product described in `README.md` and `PRD.md`.

Working rules for this file:

- Keep tasks unchecked until they are fully implemented, tested, and documented.
- Treat `benchmark mode` and `character mode` as separate concerns throughout the build.
- Treat `GCP` as the default cloud platform for the paid online product.
- Treat the public `Chess Index` as licensing-gated from the start.
- Treat the gameplay layer and the persona layer as intentionally separable.

## [ ] Immediate Build Queue

This queue pulls the highest-leverage unchecked work out of the early sprints and puts it in one place so we can move from a planning-heavy repo to a product-ready implementation lane.

### [ ] Queue A: Repository, policy, and developer workflow baseline

- [x] `1.11` Finalize top-level repository naming conventions
- [ ] `1.12` Add `LICENSE`
- [x] `1.13` Add `CODE_OF_CONDUCT.md`
- [x] `1.14` Add issue templates
- [x] `1.15` Add pull request template
- [x] `1.16` Add changelog policy
- [x] `1.17` Add release versioning policy
- [x] `1.18` Add architecture decision record directory
- [x] `1.19` Add documentation index page
- [x] `1.20` Add product glossary
- [ ] `1.22` Remove stale generated artifacts from source control
- [x] `2.4` Add editable install workflow
- [x] `2.5` Add lockfile workflow
- [x] `2.6` Add local bootstrap script
- [x] `2.7` Add task runner commands for common workflows
- [x] `2.8` Add `.env` validation script
- [x] `2.9` Expand `.env.example` comments
- [x] `2.10` Add `pre-commit` configuration
- [x] `2.13` Add type-checking configuration
- [x] `2.15` Add coverage configuration
- [x] `2.16` Add local smoke test script

### [ ] Queue B: Configuration and domain contracts needed for the real app

- [x] `3.3` Add configuration profile support
- [x] `3.4` Add benchmark-mode configuration
- [x] `3.5` Add showmatch-mode configuration
- [x] `3.6` Add interactive-mode configuration
- [x] `3.7` Add character-mode configuration
- [x] `3.8` Add feature flag support
- [x] `3.9` Add secrets redaction in logs
- [x] `3.10` Add structured logging configuration
- [ ] `3.11.3` Add named reusable model preset registry
- [ ] `3.11.4` Add preset resolution tests beyond direct model overrides
- [ ] `3.12` Add personality preset configuration support
- [ ] `3.13` Add voice preset configuration support
- [ ] `3.14` Add avatar preset configuration support
- [ ] `3.15` Add GCP deployment configuration surface
- [x] `3.16` Add settings export command
- [ ] `3.18` Add configuration migration notes
- [x] `3.19` Add game-mode enum
- [x] `3.20` Add seat-controller enum
- [x] `3.21` Add persona-role enum
- [x] `3.22` Add environment profile definitions for `dev`, `staging`, and `prod`

### [ ] Queue C: Chess correctness and replay-safe match state

- [x] `4.1.4` Add dedicated regression tests for non-starting positions
- [ ] `4.2` Add PGN import support
- [x] `4.3` Add PGN export support
- [x] `4.7` Add promotion parsing coverage
- [x] `4.8` Add en passant validation coverage
- [ ] `4.9` Add repetition detection helpers
- [ ] `4.10` Add fifty-move-rule helpers
- [ ] `4.11` Add insufficient material detection
- [ ] `4.13` Add resignation handling
- [ ] `4.14` Add abort handling
- [ ] `4.15` Add timeout adjudication
- [ ] `4.17` Add repeated-failure forfeit policy
- [ ] `4.21` Add clock state serialization helpers
- [x] `4.22` Add legality explanation formatter
- [x] `4.23` Add chess regression fixture corpus
- [ ] `4.24` Add board-state tests for control handoff safety

### [ ] Queue D: Prompt architecture, deterministic invalid-move handling, and CLI usability

- [x] `5.1.2` Move prompt construction out of `runner.py` into a dedicated prompts module
- [x] `5.1.3` Add prompt-builder-specific tests
- [x] `5.2` Add prompt version identifiers
- [x] `5.4` Add strict structured-output prompt template
- [x] `5.5` Add invalid-move retry prompt template
- [x] `5.6` Add deterministic invalid-move explanation prompt
- [x] `5.7` Add referee coaching suggestion prompt
- [ ] `5.15.4` Add richer multi-candidate ambiguity reporting
- [ ] `5.16` Add parsing taxonomy enum
- [ ] `5.17` Add candidate ranking heuristics
- [ ] `5.18` Add prompt experiment toggles
- [ ] `5.19` Add benchmark contamination checks for prompt flows
- [x] `5.20` Add forced correction-and-resubmit loop
- [x] `5.21` Add deterministic wrong-move notification path from chess engine
- [x] `5.22` Add referee callback path after engine rejection
- [ ] `5.24` Add verbose transcript output mode to CLI
- [x] `5.25` Add `replay` CLI command
- [x] `5.26` Add `inspect-game` CLI command
- [x] `5.27` Add `list-games` CLI command
- [x] `5.28` Add `export-game` CLI command
- [x] `5.30` Add CLI integration tests

### [ ] Queue E: Local runtime diagnostics and operations

- [ ] `6.2` Add async provider interface
- [x] `6.3` Add provider capability model
- [x] `6.4.2` Add finer-grained provider error categories
- [x] `6.5` Add provider health check contract
- [x] `6.6` Add retry and backoff policy contract
- [x] `6.7` Add timeout policy contract
- [ ] `6.8` Add provider selection policy
- [ ] `6.9` Add provider mock harness
- [x] `6.10.2` Add dedicated host health probe method
- [x] `6.10.3` Add health probe CLI or diagnostics command
- [x] `6.11` Add Ollama model existence check
- [ ] `6.12` Add Ollama model warmup command
- [ ] `6.13` Add Ollama context-window configuration support
- [ ] `6.14` Add Ollama thinking-output handling
- [ ] `6.15` Add Ollama local-only hardening

### [ ] Queue F: First benchmark and ratings foundation after the core runtime is hardened

- [x] `7.1` Add Stockfish process wrapper
- [x] `7.2` Add engine health checks
- [x] `7.3` Add configurable analysis depth
- [x] `7.4` Add MultiPV analysis support
- [x] `7.5` Add principal-variation formatting
- [x] `7.6` Add centipawn evaluation formatting
- [x] `7.7` Add mate-score formatting
- [x] `7.8` Add engine-anchor competitor model
- [x] `7.9` Add competitor identity model for `model + quantization + runtime + prompt profile`
- [x] `7.10` Add provisional rating flag
- [x] `7.11` Add Elo update engine
- [ ] `7.12` Add Glicko-style confidence tracking

## [ ] Sprint 1: Product Alignment & Repository Foundation (20/22 done)

### [ ] 1. Product Alignment & Repository Foundation

- [x] 1.1 Audit `README.md`, `PRD.md`, `TASKS.md`, and `file_structure.md` for contradictions
- [x] 1.2 Freeze the launch definition of `benchmark mode`
- [x] 1.3 Freeze the launch definition of `showmatch mode`
- [x] 1.4 Freeze the launch definition of `interactive mode`
- [x] 1.5 Freeze the launch definition of `character mode`
- [x] 1.6 Document the boundary between gameplay logic and persona logic
- [x] 1.7 Document the boundary between legality enforcement and referee commentary
- [x] 1.8 Document the launch scope for the public `Chess Index`
- [x] 1.9 Document the launch scope for private paid games
- [x] 1.10 Document the launch scope for personalities, voices, and avatars
- [x] 1.11 Finalize top-level repository naming conventions
- [ ] 1.12 Add `LICENSE`
- [x] 1.13 Add `CODE_OF_CONDUCT.md`
- [x] 1.14 Add issue templates
- [x] 1.15 Add pull request template
- [x] 1.16 Add changelog policy
- [x] 1.17 Add release versioning policy
- [x] 1.18 Add architecture decision record directory
- [x] 1.19 Add documentation index page
- [x] 1.20 Add product glossary
- [x] 1.21 Add contributor quickstart page
- [ ] 1.22 Remove stale generated artifacts from source control

## [ ] Sprint 2: Local Dev Environment, Tooling & CI (16/22 done)

### [ ] 2. Local Dev Environment, Tooling & CI

- [x] 2.1 Finalize Python version target
- [x] 2.2 Pin runtime dependencies in `pyproject.toml`
- [x] 2.3 Pin development dependencies in `pyproject.toml`
- [x] 2.4 Add editable install workflow
- [x] 2.5 Add lockfile workflow
- [x] 2.6 Add local bootstrap script
- [x] 2.7 Add task runner commands for common workflows
- [x] 2.8 Add `.env` validation script
- [x] 2.9 Expand `.env.example` comments
- [x] 2.10 Add `pre-commit` configuration
- [x] 2.11 Add Ruff configuration
- [x] 2.12 Add Black configuration
- [x] 2.13 Add type-checking configuration
- [x] 2.14 Add pytest configuration
- [x] 2.15 Add coverage configuration
- [x] 2.16 Add local smoke test script
- [ ] 2.17 Add CI lint workflow
- [ ] 2.18 Add CI test workflow
- [ ] 2.19 Add CI type-check workflow
- [ ] 2.20 Add Python version test matrix
- [ ] 2.21 Add dependency update workflow
- [ ] 2.22 Add release automation workflow

## [ ] Sprint 3: Configuration, Modes & Domain Contracts (26/34 done)

### [ ] 3. Configuration, Modes & Domain Contracts

- [x] 3.1 Finalize typed application settings model
- [x] 3.1.1 Add `ProviderName` enum for supported runtimes
- [x] 3.1.2 Add typed `OllamaSettings` dataclass
- [x] 3.1.3 Add typed `AppSettings` dataclass
- [x] 3.2 Add configuration precedence rules
- [x] 3.2.1 Load values from explicit `env` mapping in tests
- [x] 3.2.2 Load values from process environment when no mapping is supplied
- [x] 3.2.3 Support `LEXICHESS_MODEL` override over provider-specific model config
- [x] 3.3 Add configuration profile support
- [x] 3.4 Add benchmark-mode configuration
- [x] 3.5 Add showmatch-mode configuration
- [x] 3.6 Add interactive-mode configuration
- [x] 3.7 Add character-mode configuration
- [x] 3.8 Add feature flag support
- [x] 3.9 Add secrets redaction in logs
- [x] 3.10 Add structured logging configuration
- [ ] 3.11 Add model preset configuration support
- [x] 3.11.1 Add default provider model selection helper
- [x] 3.11.2 Add per-invocation model override support in CLI and provider builder
- [ ] 3.11.3 Add named reusable model preset registry
- [ ] 3.11.4 Add preset resolution tests beyond direct model overrides
- [ ] 3.12 Add personality preset configuration support
- [ ] 3.13 Add voice preset configuration support
- [ ] 3.14 Add avatar preset configuration support
- [ ] 3.15 Add GCP deployment configuration surface
- [x] 3.16 Add settings export command
- [x] 3.17 Add settings validation tests
- [x] 3.17.1 Add default settings load test
- [x] 3.17.2 Add global model override test
- [ ] 3.18 Add configuration migration notes
- [x] 3.19 Add game-mode enum
- [x] 3.20 Add seat-controller enum
- [x] 3.21 Add persona-role enum
- [x] 3.22 Add environment profile definitions for `dev`, `staging`, and `prod`

## [ ] Sprint 4: Chess Rules, Board State & Adjudication (23/33 done)

### [ ] 4. Chess Rules, Board State & Adjudication

- [x] 4.1 Add arbitrary starting FEN support
- [x] 4.1.1 Add `ChessBoard` initialization from optional FEN
- [x] 4.1.2 Thread optional initial FEN into the game runner
- [x] 4.1.3 Add CLI `--fen` argument
- [x] 4.1.4 Add dedicated regression tests for non-starting positions
- [ ] 4.2 Add PGN import support
- [x] 4.3 Add PGN export support
- [x] 4.4 Add SAN normalization coverage
- [x] 4.5 Add UCI normalization coverage
- [x] 4.6 Add castling notation normalization coverage
- [x] 4.7 Add promotion parsing coverage
- [x] 4.8 Add en passant validation coverage
- [ ] 4.9 Add repetition detection helpers
- [ ] 4.10 Add fifty-move-rule helpers
- [ ] 4.11 Add insufficient material detection
- [x] 4.12 Add draw claim handling
- [ ] 4.13 Add resignation handling
- [ ] 4.14 Add abort handling
- [ ] 4.15 Add timeout adjudication
- [x] 4.16 Add illegal-move forfeit policy
- [ ] 4.17 Add repeated-failure forfeit policy
- [x] 4.18 Add terminal state summary helpers
- [x] 4.18.1 Add `is_game_over()` wrapper
- [x] 4.18.2 Add `result()` wrapper
- [x] 4.18.3 Add `outcome_reason()` wrapper
- [x] 4.19 Add board snapshot serialization helpers
- [x] 4.19.1 Add `fen` property for current board snapshot
- [x] 4.20 Add move history serialization helpers
- [x] 4.20.1 Add SAN move-history replay helper
- [ ] 4.21 Add clock state serialization helpers
- [x] 4.22 Add legality explanation formatter
- [x] 4.23 Add chess regression fixture corpus
- [ ] 4.24 Add board-state tests for control handoff safety

## [ ] Sprint 5: Prompting, Move Parsing & Match Loop (33/45 done)

### [ ] 5. Prompting, Move Parsing & Match Loop

- [x] 5.1 Extract prompt builder into a dedicated module
- [x] 5.1.1 Add inline `build_move_prompt()` helper in the match runner
- [x] 5.1.2 Move prompt construction out of `runner.py` into a dedicated prompts module
- [x] 5.1.3 Add prompt-builder-specific tests
- [x] 5.2 Add prompt version identifiers
- [x] 5.3 Add benchmark-mode move-only prompt template
- [x] 5.3.1 Add benchmark-style system instruction constant
- [x] 5.3.2 Include current FEN in prompt body
- [x] 5.3.3 Include move history in prompt body
- [x] 5.3.4 Include legal SAN moves in prompt body
- [x] 5.4 Add strict structured-output prompt template
- [x] 5.5 Add invalid-move retry prompt template
- [x] 5.6 Add deterministic invalid-move explanation prompt
- [x] 5.7 Add referee coaching suggestion prompt
- [ ] 5.8 Add showmatch roast prompt
- [ ] 5.9 Add locked-move trash-talk prompt
- [ ] 5.10 Add post-game interview prompt
- [ ] 5.11 Add coach-style prompt path
- [ ] 5.12 Add character-style prompt path
- [x] 5.13 Add move extraction from fenced code blocks
- [x] 5.14 Add move extraction from quoted snippets
- [ ] 5.15 Add ambiguous output diagnostics
- [x] 5.15.1 Distinguish `empty_response`
- [x] 5.15.2 Distinguish `no_candidate_found`
- [x] 5.15.3 Distinguish `invalid_or_illegal_move`
- [ ] 5.15.4 Add richer multi-candidate ambiguity reporting
- [ ] 5.16 Add parsing taxonomy enum
- [ ] 5.17 Add candidate ranking heuristics
- [ ] 5.18 Add prompt experiment toggles
- [ ] 5.19 Add benchmark contamination checks for prompt flows
- [x] 5.20 Add forced correction-and-resubmit loop
- [x] 5.21 Add deterministic wrong-move notification path from chess engine
- [x] 5.22 Add referee callback path after engine rejection
- [x] 5.23 Add quiet JSON output mode to CLI
- [x] 5.23.1 Add `--quiet` flag to CLI
- [x] 5.23.2 Suppress summary output when `--quiet` is enabled
- [ ] 5.24 Add verbose transcript output mode to CLI
- [x] 5.25 Add `replay` CLI command
- [x] 5.26 Add `inspect-game` CLI command
- [x] 5.27 Add `list-games` CLI command
- [x] 5.28 Add `export-game` CLI command
- [x] 5.29 Add move-loop unit tests
- [x] 5.29.1 Add runner test for move-cap termination
- [x] 5.29.2 Add runner test for invalid model output logging
- [x] 5.30 Add CLI integration tests

## [ ] Sprint 6: Local Runtime Providers & GPU Operations (19/39 done)

### [ ] 6. Local Runtime Providers & GPU Operations

- [x] 6.1 Add sync provider interface
- [x] 6.1.1 Add abstract `MoveProvider` base class
- [x] 6.1.2 Add `request_move()` sync contract
- [ ] 6.2 Add async provider interface
- [x] 6.3 Add provider capability model
- [x] 6.4 Add provider error taxonomy
- [x] 6.4.1 Add `ProviderError` base runtime failure type
- [x] 6.4.2 Add finer-grained provider error categories
- [x] 6.5 Add provider health check contract
- [x] 6.6 Add retry and backoff policy contract
- [x] 6.7 Add timeout policy contract
- [ ] 6.8 Add provider selection policy
- [ ] 6.9 Add provider mock harness
- [x] 6.10 Add Ollama host health probe
- [x] 6.10.1 Normalize Ollama API base URLs consistently
- [x] 6.10.2 Add dedicated host health probe method
- [x] 6.10.3 Add health probe CLI or diagnostics command
- [x] 6.11 Add Ollama model existence check
- [ ] 6.12 Add Ollama model warmup command
- [ ] 6.13 Add Ollama context-window configuration support
- [ ] 6.14 Add Ollama thinking-output handling
- [ ] 6.15 Add Ollama local-only hardening
- [x] 6.16 Add Ollama integration tests
- [x] 6.16.1 Add test for generate endpoint payload and response handling
- [x] 6.16.2 Add test for surfaced Ollama error payloads
- [ ] 6.17 Add vLLM settings model
- [ ] 6.18 Add vLLM provider implementation
- [ ] 6.19 Add vLLM smoke-test command
- [ ] 6.20 Add vLLM integration tests
- [ ] 6.21 Add llama.cpp provider implementation
- [ ] 6.22 Add llama.cpp smoke-test command
- [ ] 6.23 Add shared runtime comparison benchmark
- [ ] 6.24 Add RTX 4090 VRAM tuning guide
- [ ] 6.25 Add per-model VRAM budget catalog
- [ ] 6.26 Add GPU worker queueing strategy
- [ ] 6.27 Add local-model process isolation strategy
- [ ] 6.28 Add concurrent worker saturation benchmark
- [x] 6.29 Add referee-model deployment preset
- [ ] 6.30 Add optional `Gemma` player deployment preset

## [ ] Sprint 7: Stockfish, Ratings & Chess Index Core (16/26 done)

### [ ] 7. Stockfish, Ratings & Chess Index Core

- [ ] 7.1 Add Stockfish binary discovery
- [x] 7.2 Add Stockfish engine configuration options
- [x] 7.3 Add engine move adapter
- [x] 7.4 Add engine-vs-model match mode
- [x] 7.5 Add centipawn evaluation logging
- [x] 7.6 Add best-line annotations
- [x] 7.7 Add MultiPV analysis mode
- [ ] 7.8 Add configurable 2-5 move lookahead
- [ ] 7.9 Add opening classification support
- [ ] 7.10 Add blunder, mistake, and inaccuracy labels
- [ ] 7.11 Add mate-threat detection helper
- [ ] 7.12 Add swing-detection helper
- [ ] 7.13 Add engine summary payload for players
- [ ] 7.14 Add engine summary payload for referee
- [x] 7.15 Define anchor engine ladder
- [ ] 7.16 Select public rating model
- [ ] 7.17 Select internal confidence model
- [x] 7.18 Add provisional rating rules
- [x] 7.19 Add competitor identity schema
- [x] 7.20 Add rating update service
- [x] 7.21 Add rating snapshot history
- [x] 7.22 Add public `Chess Index` generation logic
- [x] 7.23 Add rating export format
- [x] 7.24 Add rating tests
- [x] 7.25 Add benchmark summary report template
- [x] 7.26 Add Chess Index reproducibility manifest

## [ ] Sprint 8: Model Intake, Licensing & Roster Governance (9/24 done)

### [ ] 8. Model Intake, Licensing & Roster Governance

- [ ] 8.1 Add model catalog schema
- [ ] 8.2 Add license catalog schema
- [ ] 8.3 Add official source field
- [ ] 8.4 Add release date field
- [ ] 8.5 Add revision field
- [ ] 8.6 Add quantization field
- [ ] 8.7 Add runtime field
- [ ] 8.8 Add hardware-class field
- [ ] 8.9 Add public-index admission status field
- [ ] 8.10 Add legal-review status field
- [x] 8.11 Add intake checklist document
- [x] 8.12 Add official release watch workflow
- [ ] 8.13 Add manual intake admin flow
- [x] 8.14 Add official weights download workflow
- [x] 8.15 Add approved quantization workflow
- [x] 8.16 Add smoke-test workflow for new models
- [x] 8.17 Add placement-match workflow for new models
- [x] 8.18 Add provisional rating publication workflow
- [x] 8.19 Add full ladder promotion workflow
- [ ] 8.20 Add model deprecation workflow
- [ ] 8.21 Add broken-model quarantine workflow
- [x] 8.22 Add license disclosure surface requirements
- [ ] 8.23 Add intake audit log
- [ ] 8.24 Add model intake tests

## [ ] Sprint 9: Data Schema, Migrations & Replay Persistence (16/35 done)

### [ ] 9. Data Schema, Migrations & Replay Persistence

- [ ] 9.1 Choose migration framework
- [ ] 9.2 Add migration directory
- [x] 9.3 Finalize `games` table
- [x] 9.3.1 Persist white provider and model fields
- [x] 9.3.2 Persist black provider and model fields
- [x] 9.3.3 Persist initial FEN
- [x] 9.3.4 Persist game status, result, and termination reason
- [x] 9.3.5 Persist started and ended timestamps
- [x] 9.4 Finalize `turns` table
- [x] 9.4.1 Persist prompt and instructions for each turn
- [x] 9.4.2 Persist raw response text and optional raw response JSON
- [x] 9.4.3 Persist candidate move, SAN, and UCI fields
- [x] 9.4.4 Persist FEN before and after move evaluation
- [x] 9.4.5 Persist legality, latency, and error fields
- [x] 9.4.6 Add repository reads for turns by game id
- [ ] 9.5 Add `illegal_move_attempts` table
- [ ] 9.6 Add `control_handoffs` table
- [ ] 9.7 Add `chat_messages` table
- [ ] 9.8 Add `referee_events` table
- [ ] 9.9 Add `banter_events` table
- [x] 9.10 Add `engine_analyses` table
- [x] 9.11 Add `ratings` table
- [ ] 9.12 Add `model_catalog` table
- [ ] 9.13 Add `personality_catalog` table
- [ ] 9.14 Add `voice_catalog` table
- [ ] 9.15 Add `avatar_catalog` table
- [ ] 9.16 Add `replay_manifests` table
- [ ] 9.17 Add `audio_assets` table
- [ ] 9.18 Add `clips_and_bookmarks` table
- [x] 9.19 Add repository abstractions for new tables
- [ ] 9.20 Add seed data scripts
- [ ] 9.21 Add migration tests
- [ ] 9.22 Add backup and restore scripts for local development
- [ ] 9.23 Add data retention notes
- [ ] 9.24 Add replay package structure definition

## [ ] Sprint 10: Tournament Scheduling & Batch Orchestration (16/22 done)

### [ ] 10. Tournament Scheduling & Batch Orchestration

- [x] 10.1 Add tournament entity
- [x] 10.2 Add roster entry entity
- [x] 10.3 Add pairing entity
- [x] 10.4 Add standings entity
- [ ] 10.5 Add round state entity
- [x] 10.6 Add round-robin scheduler
- [x] 10.7 Add engine-anchor scheduling mode
- [x] 10.8 Add named tournament presets
- [x] 10.9 Add batch single-game execution command
- [x] 10.10 Add resumable tournament runs
- [x] 10.11 Add paused tournament resume flow
- [x] 10.12 Add tournament seeding rules
- [x] 10.13 Add tournament tie-break rules
- [ ] 10.14 Add compute-aware scheduling rules
- [ ] 10.15 Add per-worker concurrency caps
- [x] 10.16 Add tournament CLI commands
- [x] 10.17 Add tournament export format
- [ ] 10.18 Add tournament API contracts
- [ ] 10.19 Add private tournament support
- [ ] 10.20 Add featured event scheduling support
- [x] 10.21 Add tournament integration tests
- [x] 10.22 Add tournament failure recovery rules

## [ ] Sprint 11: GCP Foundation & Deployment Baseline (0/30 done)

### [ ] 11. GCP Foundation & Deployment Baseline

- [ ] 11.1 Choose primary `GCP` region
- [ ] 11.2 Choose backup `GCP` region
- [ ] 11.3 Define project naming standards
- [ ] 11.4 Create `dev` project
- [ ] 11.5 Create `staging` project
- [ ] 11.6 Create `prod` project
- [ ] 11.7 Configure budget alerts
- [ ] 11.8 Create `Artifact Registry` repositories
- [ ] 11.9 Create `Cloud Storage` buckets for media and replay assets
- [ ] 11.10 Create `Cloud SQL for PostgreSQL` instances
- [ ] 11.11 Create `Secret Manager` secrets
- [ ] 11.12 Create service accounts
- [ ] 11.13 Define IAM role bindings
- [ ] 11.14 Create networking baseline
- [ ] 11.15 Containerize web app
- [ ] 11.16 Containerize backend app services
- [ ] 11.17 Containerize worker services
- [ ] 11.18 Create `Cloud Run` service baseline
- [ ] 11.19 Create `Cloud SQL` connectivity baseline
- [ ] 11.20 Create `Cloud Storage` lifecycle rules
- [ ] 11.21 Create `Compute Engine Spot VM` template for GPU workers
- [ ] 11.22 Add GPU worker startup scripts
- [ ] 11.23 Add VM image build pipeline
- [ ] 11.24 Add CI deploy pipeline to `Cloud Run`
- [ ] 11.25 Set up domain and DNS
- [ ] 11.26 Set up TLS certificates
- [ ] 11.27 Add staging smoke tests
- [ ] 11.28 Add rollback procedure
- [ ] 11.29 Evaluate `Cloud Run GPU` fit for bursty referee workloads
- [ ] 11.30 Add infrastructure-as-code modules

## [ ] Sprint 12: Website Backend API Foundation (22/30 done)

### [ ] 12. Website Backend API Foundation

- [x] 12.1 Choose API framework
- [x] 12.2 Scaffold API application package
- [x] 12.3 Add health endpoint
- [x] 12.4 Add version endpoint
- [ ] 12.5 Add current-user endpoint
- [x] 12.6 Add game creation endpoint
- [x] 12.7 Add game detail endpoint
- [x] 12.8 Add game list endpoint
- [x] 12.9 Add replay endpoint
- [x] 12.10 Add live game event stream endpoint
- [x] 12.11 Add live referee stream endpoint
- [x] 12.12 Add player banter stream endpoint
- [ ] 12.13 Add engine lookahead endpoint
- [x] 12.14 Add seat-claim endpoint
- [x] 12.15 Add seat-release-to-LLM endpoint
- [x] 12.16 Add user-to-player chat endpoint
- [x] 12.17 Add showmatch transcript endpoint
- [ ] 12.18 Add recording manifest endpoint
- [x] 12.19 Add leaderboard endpoint
- [ ] 12.20 Add model catalog endpoint
- [ ] 12.21 Add personality catalog endpoint
- [ ] 12.22 Add saved replay library endpoint
- [ ] 12.23 Add saved clip library endpoint
- [x] 12.24 Add OpenAPI schema
- [x] 12.25 Add API integration tests
- [ ] 12.26 Add auth middleware and request guards
- [x] 12.27 Add human move submission endpoint
- [x] 12.28 Add live loop control endpoints
- [x] 12.29 Add background live execution manager
- [x] 12.30 Add model-turn worker orchestration

## [ ] Sprint 13: Accounts, Auth, Billing & Entitlements (0/30 done)

### [ ] 13. Accounts, Auth, Billing & Entitlements

- [ ] 13.1 Add user model
- [ ] 13.2 Add password hashing policy
- [ ] 13.3 Add registration flow
- [ ] 13.4 Add email verification flow
- [ ] 13.5 Add login flow
- [ ] 13.6 Add logout flow
- [ ] 13.7 Add session refresh flow
- [ ] 13.8 Add forgot-password flow
- [ ] 13.9 Add reset-password flow
- [ ] 13.10 Add active-session management flow
- [ ] 13.11 Add profile settings model
- [ ] 13.12 Add notification preferences model
- [ ] 13.13 Choose payment provider
- [ ] 13.14 Define subscription plans
- [ ] 13.15 Define entitlement matrix
- [ ] 13.16 Add checkout flow
- [ ] 13.17 Add billing portal flow
- [ ] 13.18 Add invoice history flow
- [ ] 13.19 Add usage metering model
- [ ] 13.20 Add quota enforcement service
- [ ] 13.21 Add premium personality entitlements
- [ ] 13.22 Add premium voice entitlements
- [ ] 13.23 Add premium private-room entitlements
- [ ] 13.24 Add billing webhook handling
- [ ] 13.25 Add failed-payment recovery flow
- [ ] 13.26 Add grace-period rules
- [ ] 13.27 Add account deletion flow
- [ ] 13.28 Add user data export flow
- [ ] 13.29 Add subscription tests
- [ ] 13.30 Add auth security tests

## [ ] Sprint 14: Frontend Foundation & Design System (7/22 done)

### [ ] 14. Frontend Foundation & Design System

- [x] 14.1 Choose frontend stack
- [x] 14.2 Scaffold frontend application
- [x] 14.3 Add design tokens
- [ ] 14.4 Add brand theme system
- [x] 14.5 Add application shell
- [x] 14.6 Add routing
- [ ] 14.7 Add auth state handling
- [ ] 14.8 Add protected-route guards
- [ ] 14.9 Add API client layer
- [ ] 14.10 Add realtime transport layer
- [ ] 14.11 Add component library foundation
- [ ] 14.12 Add loading states
- [x] 14.13 Add empty states
- [ ] 14.14 Add error states
- [x] 14.15 Add responsive navigation
- [ ] 14.16 Add accessibility baseline
- [ ] 14.17 Add frontend testing harness
- [ ] 14.18 Add performance budget
- [ ] 14.19 Add settings route
- [ ] 14.20 Add billing route
- [ ] 14.21 Add personal library route
- [ ] 14.22 Add frontend architecture documentation

## [ ] Sprint 15: Live Game UI, Replays & Human Handoffs (0/30 done)

### [ ] 15. Live Game UI, Replays & Human Handoffs

- [ ] 15.1 Build chessboard component
- [ ] 15.2 Build move list panel
- [ ] 15.3 Build turn status panel
- [ ] 15.4 Build player identity card
- [ ] 15.5 Build controller badge
- [ ] 15.6 Build seat-claim controls
- [ ] 15.7 Build hand-control-to-LLM modal
- [ ] 15.8 Build character selection surface
- [ ] 15.9 Build chat target selector
- [ ] 15.10 Build user-to-player chat composer
- [ ] 15.11 Build referee panel
- [ ] 15.12 Build player banter panel
- [ ] 15.13 Build engine evaluation panel
- [ ] 15.14 Build next 2-5 moves preview panel
- [ ] 15.15 Build illegal-move banner
- [ ] 15.16 Build correction thread card
- [ ] 15.17 Build forced resubmission status indicator
- [ ] 15.18 Build control-handoff timeline rail
- [ ] 15.19 Build replay scrubber
- [ ] 15.20 Build replay bookmarks
- [ ] 15.21 Build private room lobby screen
- [ ] 15.22 Build invite-link join flow
- [ ] 15.23 Build benchmark-mode badge
- [ ] 15.24 Build showmatch-mode badge
- [ ] 15.25 Build interactive-mode badge
- [ ] 15.26 Build spectator count indicator
- [ ] 15.27 Build endgame celebration surface
- [ ] 15.28 Build clip creation action
- [ ] 15.29 Build transcript export action
- [ ] 15.30 Add live game UI tests

## [ ] Sprint 16: Personality System, Memory & Character Packs (12/32 done)

### [ ] 16. Personality System, Memory & Character Packs

- [ ] 16.1 Add personality catalog schema
- [x] 16.2 Define launch personality roster
- [x] 16.2.1 Reserve `Gemma 4` for referee by default
- [x] 16.2.2 Reserve optional `Gemma` player preset for showmatches
- [x] 16.2.3 Document first-wave character concepts in README and PRD
- [ ] 16.3 Define `Serious Coach` persona
- [ ] 16.4 Define `Calm Master` persona
- [ ] 16.5 Define `Wholesome Encourager` persona
- [ ] 16.6 Define `Snarky Rival` persona
- [ ] 16.7 Define `Blitz Goblin` persona
- [ ] 16.8 Define `Sports Energy` persona
- [x] 16.9 Define `Gemma 4` referee persona
- [x] 16.9.1 Define `Gemma 4` as mediator and adult in the room
- [x] 16.9.2 Define `Gemma 4` as deterministic-rule-break responder
- [x] 16.10 Define optional `Gemma` player persona
- [x] 16.10.1 Define optional `Gemma` player as separate from referee role
- [x] 16.11 Add gameplay-to-persona binding rules
- [x] 16.11.1 Document gameplay-layer vs persona-layer separation
- [x] 16.11.2 Document benchmark-mode vs character-mode separation
- [ ] 16.12 Add persona system prompt templates
- [ ] 16.13 Add catchphrase library
- [ ] 16.14 Add tone rules
- [ ] 16.15 Add anti-repetition rules
- [ ] 16.16 Add user personality preference storage
- [ ] 16.17 Add character memory strategy
- [ ] 16.18 Add coaching-style preference support
- [ ] 16.19 Add personality preview cards
- [ ] 16.20 Add premium character pack framework
- [ ] 16.21 Add personality QA checklist
- [ ] 16.22 Add personality regression tests
- [ ] 16.23 Add persona moderation rules
- [ ] 16.24 Add character analytics hooks

## [ ] Sprint 17: Voice, TTS & Avatar Presentation (0/24 done)

### [ ] 17. Voice, TTS & Avatar Presentation

- [ ] 17.1 Choose TTS stack for v1
- [ ] 17.2 Choose voice-input scope for v1
- [ ] 17.3 Add voice preset catalog
- [ ] 17.4 Map voices to personalities
- [ ] 17.5 Add TTS generation service
- [ ] 17.6 Add streaming audio chunking
- [ ] 17.7 Add audio caching
- [ ] 17.8 Add audio delivery endpoint
- [ ] 17.9 Add browser audio controls
- [ ] 17.10 Add subtitle sync
- [ ] 17.11 Add speaking indicator
- [ ] 17.12 Add lightweight avatar portrait system
- [ ] 17.13 Add avatar reaction states
- [ ] 17.14 Add idle, thinking, and talking states
- [ ] 17.15 Add avatar asset pipeline
- [ ] 17.16 Add premium avatar pack framework
- [ ] 17.17 Add text-only fallback for TTS failures
- [ ] 17.18 Add autoplay fallback UX
- [ ] 17.19 Add TTS cost metering
- [ ] 17.20 Add voice moderation checks
- [ ] 17.21 Add character voice QA pass
- [ ] 17.22 Add avatar accessibility fallback
- [ ] 17.23 Add replay audio scrubber
- [ ] 17.24 Add advanced animated avatar gate for post-launch expansion

## [ ] Sprint 18: Referee, Showmatches & Broadcast Engine (21/28 done)

### [ ] 18. Referee, Showmatches & Broadcast Engine

- [x] 18.1 Add referee service abstraction
- [x] 18.2 Add `Gemma 4` referee deployment preset
- [ ] 18.3 Add deterministic rule-break event contract
- [x] 18.4 Add referee explanation payload contract
- [x] 18.5 Add referee coaching suggestion payload contract
- [x] 18.6 Add player-banter orchestration service
- [x] 18.7 Add post-move roast pipeline
- [x] 18.8 Add pregame intro script workflow
- [x] 18.9 Add midgame hype script workflow
- [x] 18.10 Add illegal-move callout script workflow
- [x] 18.11 Add checkmate finisher script workflow
- [x] 18.12 Add draw-result wrap-up workflow
- [x] 18.13 Add post-game interview workflow
- [x] 18.14 Add rivalry recap workflow
- [x] 18.15 Add quote pinning workflow
- [x] 18.16 Add highlight moment detection
- [x] 18.17 Add clip manifest generation
- [x] 18.18 Add broadcast timeline schema
- [x] 18.19 Add transcript-to-audio sync
- [x] 18.20 Add featured showmatch page
- [x] 18.21 Add live broadcast control surface
- [x] 18.22 Add showmatch moderation queue
- [ ] 18.23 Add live referee override controls
- [ ] 18.24 Add crowd-hype copy library
- [ ] 18.25 Add benchmark contamination tests for showmatch layer
- [ ] 18.26 Add premium featured-match entitlement gates
- [ ] 18.27 Add showmatch analytics dashboard
- [ ] 18.28 Add showmatch QA checklist

## [ ] Sprint 19: Public Chess Index, Community & Discovery (3/24 done)

### [ ] 19. Public Chess Index, Community & Discovery

- [x] 19.1 Build public leaderboard page
- [ ] 19.2 Build model profile page
- [ ] 19.3 Build competitor configuration disclosure surface
- [ ] 19.4 Build license disclosure surface
- [ ] 19.5 Build rating history chart
- [ ] 19.6 Build compare-two-models page
- [ ] 19.7 Build benchmark report page
- [x] 19.8 Build tournament watch page
- [x] 19.9 Build public replay page
- [ ] 19.10 Build share-link system
- [ ] 19.11 Build highlights and clips page
- [ ] 19.12 Build rivalry page
- [ ] 19.13 Build featured character page
- [ ] 19.14 Build public schedule page
- [ ] 19.15 Add live spectator chat moderation rules
- [ ] 19.16 Add abuse reporting flow
- [ ] 19.17 Add community guidelines document
- [ ] 19.18 Add public/private visibility controls
- [ ] 19.19 Add follow-or-favorite character feature
- [ ] 19.20 Add browser notification support
- [ ] 19.21 Add SEO metadata system
- [ ] 19.22 Add sitemap and robots configuration
- [ ] 19.23 Add web analytics controls
- [ ] 19.24 Add community QA pass

## [ ] Sprint 20: Admin, Support & Internal Operations (0/24 done)

### [ ] 20. Admin, Support & Internal Operations

- [ ] 20.1 Add admin auth and role model
- [ ] 20.2 Add user management page
- [ ] 20.3 Add subscription support page
- [ ] 20.4 Add model catalog admin page
- [ ] 20.5 Add personality catalog admin page
- [ ] 20.6 Add voice preset admin page
- [ ] 20.7 Add avatar asset admin page
- [ ] 20.8 Add prompt admin page
- [ ] 20.9 Add tournament operations console
- [ ] 20.10 Add live match operations console
- [ ] 20.11 Add GPU capacity dashboard
- [ ] 20.12 Add worker queue dashboard
- [ ] 20.13 Add incident note log
- [ ] 20.14 Add audit log explorer
- [ ] 20.15 Add moderation review queue
- [ ] 20.16 Add banter moderation controls
- [ ] 20.17 Add clip approval controls
- [ ] 20.18 Add refund and comp admin tools
- [ ] 20.19 Add feature flag admin page
- [ ] 20.20 Add system health page
- [ ] 20.21 Add model intake admin tools
- [ ] 20.22 Add legal-review status admin tools
- [ ] 20.23 Add billing admin page
- [ ] 20.24 Add support runbook docs

## [ ] Sprint 21: Reliability, Security & Privacy Hardening (0/31 done)

### [ ] 21. Reliability, Security & Privacy Hardening

- [ ] 21.1 Choose background job framework
- [ ] 21.2 Add worker service
- [ ] 21.3 Add dead-letter queue
- [ ] 21.4 Add retry policies
- [ ] 21.5 Add scheduled jobs
- [ ] 21.6 Add backup schedule
- [ ] 21.7 Add restore drill
- [ ] 21.8 Add structured logging standard
- [ ] 21.9 Add metrics collection
- [ ] 21.10 Add tracing
- [ ] 21.11 Add alert rules
- [ ] 21.12 Add load testing
- [ ] 21.13 Add realtime reconnect handling
- [ ] 21.14 Add event ordering guarantees
- [ ] 21.15 Add GPU backpressure handling
- [ ] 21.16 Add TTS timeout fallback
- [ ] 21.17 Add inference timeout fallback
- [ ] 21.18 Add dependency scanning
- [ ] 21.19 Add secret scanning
- [ ] 21.20 Add CSRF protection
- [ ] 21.21 Add XSS protection
- [ ] 21.22 Add session hardening
- [ ] 21.23 Add rate limiting
- [ ] 21.24 Add fraud and abuse checks
- [ ] 21.25 Add privacy policy draft
- [ ] 21.26 Add terms of service draft
- [ ] 21.27 Add consent capture flows
- [ ] 21.28 Add retention and deletion policies
- [ ] 21.29 Add transcript redaction and deletion flows
- [ ] 21.30 Add account-takeover response playbook
- [ ] 21.31 Add security review checklist

## [ ] Sprint 22: Launch Preparation, Analytics & Growth (0/26 done)

### [ ] 22. Launch Preparation, Analytics & Growth

- [ ] 22.1 Build landing page
- [ ] 22.2 Build pricing page
- [ ] 22.3 Build onboarding flow
- [ ] 22.4 Build support and contact flow
- [ ] 22.5 Build documentation site
- [ ] 22.6 Add known issues page
- [ ] 22.7 Add release notes workflow
- [ ] 22.8 Add internal QA checklist
- [ ] 22.9 Add private alpha checklist
- [ ] 22.10 Add beta checklist
- [ ] 22.11 Add load rehearsal plan
- [ ] 22.12 Add launch-day runbook
- [ ] 22.13 Add post-launch monitoring checklist
- [ ] 22.14 Add first-paid-user onboarding checklist
- [ ] 22.15 Add conversion instrumentation
- [ ] 22.16 Add retention instrumentation
- [ ] 22.17 Add churn instrumentation
- [ ] 22.18 Add feedback widget
- [ ] 22.19 Add first featured-match content plan
- [ ] 22.20 Add first character-tuning pass
- [ ] 22.21 Add first public `Chess Index` season plan
- [ ] 22.22 Add first `20-30` model intake plan
- [ ] 22.23 Add post-launch cost review
- [ ] 22.24 Add post-launch roadmap refresh
- [ ] 22.25 Add public bug bash
- [ ] 22.26 Add launch retro template

## [ ] Sprint 23: Post-Launch Expansion Tracks (0/18 done)

### [ ] 23. Post-Launch Expansion Tracks

- [ ] 23.1 Add tutoring lesson domain
- [ ] 23.2 Add puzzle domain
- [ ] 23.3 Add guided coaching mode
- [ ] 23.4 Add tutor-specific personalities
- [ ] 23.5 Add lesson progress tracking
- [ ] 23.6 Add voice-input tutoring flow
- [ ] 23.7 Add advanced animated avatar pipeline
- [ ] 23.8 Add richer lip-sync workflow
- [ ] 23.9 Add longer-term character memory system
- [ ] 23.10 Add team and organization workspaces
- [ ] 23.11 Add API and SDK surface for power users
- [ ] 23.12 Add webhook support
- [ ] 23.13 Add enterprise billing and invoicing options
- [ ] 23.14 Add private customer model-roster uploads
- [ ] 23.15 Add classroom mode
- [ ] 23.16 Add sponsored broadcast surfaces
- [ ] 23.17 Add referral or affiliate flows
- [ ] 23.18 Add v2 roadmap review
