# LexiChess Product Requirements Document

Version: `0.1`
Status: `Draft`
Last Updated: `2026-04-25`
Source of Truth: [README.md](./README.md)

## 1. Overview

LexiChess is building the arena for self-hosted LLM chess: part benchmark lab, part live sports broadcast, and part interactive game room for unforgettable AI chess personalities.

It is a self-hosted chess application and research platform built around large language models. It starts from a backend MVP that can run model-vs-model games from the command line, validate moves with deterministic chess rules, and log hallucinations. It is intended to grow into a paid, authenticated website where people can:

- watch LLM chess matches live
- play against LLMs
- jump into live games midstream
- hand control of a seat back to an LLM
- talk to the player models and the referee through the web interface
- choose different AI chess personalities, voices, and avatar styles
- follow a public `Chess Index` that rates permissively licensed self-hosted models against one another

The signature product experience is not just chess strength. It is the combination of:

- rigorous move validation
- reproducible benchmarking
- self-hosted model operations
- spectator-friendly live broadcasts
- a comedy-forward showmatch layer
- a personality-driven play layer that makes users care which character they are playing with
- a rational `Gemma 4` referee who mediates, corrects illegal moves, and keeps the chaos grounded
- a `GCP`-first deployment strategy that keeps launch overhead low while preserving self-hosted control
- a chess-first social environment that explicitly avoids politics, wagering, and generic internet sludge

In short, LexiChess aims to make LLM benchmarking rigorous enough for builders and entertaining enough for everyone else.

LexiChess should feel like a product category, not a novelty wrapper around chess. The product promise is that structured evaluation, spectator delight, and character-driven play do not need to fight each other. The same underlying chess truth can power a public benchmark ladder, a premium interactive game room, a comedy-heavy showmatch, and a coaching experience with real continuity and memory.

The front-of-house story matters here. A user should immediately understand that LexiChess is not just asking, "Can this model play chess?" It is asking, "How strong is it, how reliable is it, how entertaining is it, what kind of opponent or companion does it feel like, and do I want to come back tomorrow to watch or play again?" That combination of rigor, personality, and replayability is the core product bet.

The product thesis in one line: **LexiChess becomes the home of self-hosted AI chess, where open models compete, characters perform, and every game can double as both benchmark evidence and content.**

LexiChess must also be built as a wholly original, `LLM-first` product. It is not intended to be a remake, sequel, clone, compatibility layer, or unofficial continuation of any historical chess software line. Similar user outcomes such as warmth, humor, coaching quality, and memorable character play should come from original curriculum, original personas, original voice direction, original visuals, and original system design.

## 2. Product Thesis

Most LLM evaluations are difficult to watch, hard to compare, and disconnected from real user delight. Chess gives LexiChess a structured environment for benchmarking model behavior while also creating an inherently replayable spectator product.

LexiChess should sit at the intersection of:

- `benchmarking`: measure how well models play, how often they hallucinate, and how reliably they recover
- `entertainment`: make matches fun to watch, hear, and share
- `participation`: let humans step into and out of live games
- `operations`: run the full stack on infrastructure we control
- `characters`: let users build affinity for distinct AI chess personalities
- `governance`: admit only licensing-safe models into the public ladder by default

The product should feel differentiated by four things:

- deterministic chess truth instead of vibes-based move validation
- a public `Chess Index` built around reproducibility, not hype
- a comedy-forward showmatch layer that stays separate from benchmark mode
- a grounded referee persona that keeps the chaos understandable
- a separable character layer so the same chess core can power many different personalities

## 3. Problem Statement

Developers and enthusiasts currently face several gaps:

1. There is no compelling public ladder focused on LLM chess play that combines strength, legality, and reproducibility.
2. Open-weight model releases arrive constantly, but there is no opinionated intake system that quickly evaluates them in a consistent competitive framework.
3. Existing LLM benchmarks are rarely entertaining enough to attract a broad audience.
4. Most AI product surfaces default to opaque cloud APIs instead of self-hosted local and on-prem runtimes.
5. Human players cannot usually fluidly swap control with models in the middle of a game while preserving continuity and replayability.
6. Model hallucinations are often logged as failures, but not turned into visible, teachable, funny, or shareable moments.
7. Most chess-with-AI experiences feel generic and forgettable instead of character-driven, social, and worth returning to.
8. Many online communities that could support chess discussion become unusable because they drift into politics, harassment, betting, cheating, or generic off-topic noise.

## 4. Vision

LexiChess becomes the home of the `Chess Index`: a rolling public ladder of self-hosted, permissively licensed LLMs competing in deterministic chess environments, surrounded by a website product where:

- serious users can benchmark new models
- casual users can watch featured showmatches
- subscribed users can create private games and invite others
- humans can take over seats at any point in a live match
- users can choose personalities they want to face, learn from, or team up with
- a referee model explains rule breaks and mediates player banter
- every game becomes both a research artifact and a piece of content
- community interaction remains anchored to chess, lessons, clubs, clips, and game discussion instead of general-purpose posting

## 5. Goals

### 5.1 Product Goals

- Build a website-first product on top of the current backend MVP
- Create a compelling spectator experience around LLM chess
- Make human-in-the-loop participation a core interaction, not a side feature
- Establish `Gemma 4` as the default referee persona
- Maintain a public `Chess Index` that can ingest new permissively licensed models over time
- Support a paid product model with accounts, subscriptions, entitlements, and user-owned game history
- Build a character system that gives users memorable AI personalities, not just unnamed model endpoints
- Build a chess-only community with clear moderation boundaries and strong fair-play expectations
- Build a warm, structured coaching and lesson layer on top of the core gameplay product
- Build an original product category with its own brand, voices, lessons, characters, and community identity

### 5.2 User Goals

- Watch funny, high-signal LLM matches online
- Compare models in a structured, repeatable ladder
- Play against LLMs or collaborate with them
- Choose AI personalities with different voices, tones, and coaching styles
- Jump into an ongoing game without restarting it
- See exactly when a move was illegal and how the referee handled it
- Replay matches with transcript, audio, analysis, and control handoff history
- Learn chess in a coach-first environment that feels encouraging and memorable
- Participate in a chess-only community without politics, betting, or generic social-media noise

### 5.3 Technical Goals

- Keep legality deterministic and engine-driven
- Keep model execution self-hosted
- Keep the runtime abstraction provider-agnostic
- Preserve reproducibility across model revisions, runtimes, quantizations, and hardware classes
- Build around licensing-safe model governance for the public ladder
- Use `GCP` as the primary deployment target for the paid online product
- Keep competitive human play off a public gameplay API surface

## 6. Non-Goals

The following are explicitly out of scope for the first major product release unless reprioritized:

- a mobile-native application
- dependency on third-party LLM APIs for core gameplay
- broad non-chess general-purpose chat use cases
- a full tutoring curriculum as part of the initial launch
- high-fidelity 3D avatar production as a launch blocker
- claiming that public ratings equal official FIDE Elo
- player-to-player betting, wagering, or cash-prize match mechanics in the initial product
- a public gameplay API that makes rated human play easy to automate against
- recreating or implying continuity with any legacy chess software brand without rights
- using third-party marks, likenesses, voiceprints, scripts, or trade dress without permission

## 7. Target Users

### 7.1 Spectators

People who want to watch absurd, funny, or high-stakes model-vs-model chess games, follow rivalries, and consume clips or replays.

### 7.2 Power Users

Users who want to compare self-hosted models, test quantizations, and understand how new releases perform in structured gameplay.

### 7.3 Interactive Players

Users who want to play against a model, play alongside a model, or jump into a live game already in progress.

### 7.4 Character-Driven Players

Users who care less about benchmarking and more about which personality they are playing with, how that character talks, and whether the experience feels funny, warm, intense, or coach-like.

### 7.5 Researchers and Builders

Users who care about hallucination tracking, prompt effects, legality failure modes, and reproducible benchmarking.

### 7.6 Operators and Admins

Internal users who manage inference capacity, prompts, model rosters, subscriptions, moderation, and featured match scheduling.

## 8. Core Product Principles

### 8.1 Deterministic Truth First

The chess engine is the source of truth for legality and board state. Models never determine legal moves themselves.

### 8.2 Self-Hosted by Default

Gameplay, referee behavior, analysis, and model orchestration should run on infrastructure we control.

### 8.3 Benchmarking and Showmanship Must Coexist

The product must support both clean evaluation and theatrical showmatches without contaminating benchmark data.

### 8.4 Licensing Is a Product Boundary

The public ladder is constrained by what we are comfortable self-hosting in a paid product.

### 8.5 Human Agency Matters

Users should be able to enter, leave, and delegate control inside games fluidly.

### 8.6 Replays Are First-Class

Every match should be structured so it can be replayed, analyzed, clipped, and shared.

### 8.7 Skill And Character Should Be Separable

The gameplay layer and the character layer should be related but distinct. Chess ability, persona, voice, and avatar presentation should not be tangled together so tightly that the product becomes hard to benchmark, maintain, or expand.

### 8.8 Chess-Only Community Focus

The product should remain intentionally narrow. Social features should deepen chess participation, not turn LexiChess into a general-purpose social network.

### 8.9 AI-First Product Sequencing

The product should reach a strong level of quality in AI play, coaching, replays, and character experiences before investing deeply in human-to-human voice and webcam features.

### 8.10 Original IP-Safe Product Design

Brand, characters, lessons, voices, avatars, and marketing copy must be original to LexiChess. The product should not imply endorsement, affiliation, or identity overlap with real people, prior chess brands, or legacy software properties unless explicit written rights have been secured.

## 9. Product Modes

### 9.1 Benchmark Mode

Purpose:

- produce clean ratings and research-grade logs

Characteristics:

- move-only prompting
- no banter
- no spectator contamination
- deterministic legality handling
- full structured logging

### 9.2 Showmatch Mode

Purpose:

- create entertaining public or premium broadcasts

Characteristics:

- players are allowed to roast each other
- referee is active and grounded
- audio and highlight generation are enabled
- optional `Gemma` player preset may participate

### 9.3 Interactive Mode

Purpose:

- let humans participate live

Characteristics:

- users can start as players
- users can take over a side midgame
- users can hand a side back to an LLM
- user chat can target players or referee
- control handoffs are logged and replayable

### 9.4 Human Social Play

Purpose:

- allow human players to play, discuss, and socialize around chess without diluting the AI-first product core

Characteristics:

- initially centered on direct challenges, private rooms, and game-linked discussion
- optional voice and webcam support later, after the core AI and replay experience is strong
- moderated under a chess-only code of conduct

## 10. Core Concepts

### 10.1 Chess Index

A public ladder of permissively licensed, self-hosted, reproducibly configured competitors.

Each competitor must be uniquely defined by:

- official model identifier
- publisher
- release or revision
- quantization
- runtime
- prompt profile
- hardware class

### 10.2 Competitor Identity

Ratings should attach to a full configuration, not just a marketing model name. A quantized 8B model on one runtime is not automatically the same competitor as the same family on another runtime and hardware profile.

### 10.3 Referee

`Gemma 4` is the default referee persona for the product. The referee:

- reacts only after deterministic engine events
- explains illegal moves
- asks the player to fix them
- mediates banter
- acts as coach, rational voice, and adult in the room

### 10.4 Optional Gemma Player

Separate from the referee, an optional `Gemma` player preset may be used as a player in showmatches or special events.

### 10.5 Control Handoff

A seat can be controlled by:

- a human
- an LLM

Control can shift during a game without resetting board state. The complete handoff timeline must be preserved.

### 10.6 Persona Stack

Every user-facing chess character should be built from separable layers:

- `gameplay layer`: generates or suggests moves
- `persona layer`: controls tone, catchphrases, coaching style, and banter rules
- `voice layer`: controls how the character sounds
- `avatar layer`: controls how the character looks and reacts
- `memory layer`: stores preferences, recurring context, and longer-term user affinity signals

This allows LexiChess to reuse the same chess core across multiple personalities while keeping benchmark mode clean.

## 11. Key User Stories

### 11.1 Spectator Stories

- As a spectator, I want to watch a live LLM match with commentary, referee callouts, and a move timeline.
- As a spectator, I want to hear the referee in the browser and follow along without reading everything.
- As a spectator, I want to replay a match and jump to blunders, illegal moves, or checkmate.
- As a spectator, I want to compare models in the `Chess Index`.
- As a spectator, I want to follow favorite characters and rivalries, not just anonymous model names.

### 11.2 Player Stories

- As a player, I want to start a game against an LLM from the website.
- As a player, I want to enter an LLM-vs-LLM game in progress and take over one side.
- As a player, I want to hand a side back to a model without starting over.
- As a player, I want to chat with the model on my side before deciding whether I or the model should move.
- As a player, I want to choose whether I am playing with a serious coach, a calm master, a trash-talker, or another personality.
- As a player, I want post-game review and lessons that feel warm and human instead of robotic.
- As a player, I want to talk about games with other players without the platform turning into politics or general internet fighting.

### 11.3 Power User Stories

- As a power user, I want to compare model revisions and quantizations.
- As a power user, I want to know how often a model makes illegal moves.
- As a power user, I want to understand how a new model enters the `Chess Index`.

### 11.4 Admin Stories

- As an operator, I want to add newly released permissively licensed models to the roster quickly.
- As an operator, I want to control which models are available in which plans.
- As an operator, I want to control which personalities, voices, and avatars are available in which plans.
- As an operator, I want to observe system health, match operations, and GPU load during featured events.
- As an operator, I want clear moderation and fair-play tools for politics violations, harassment, cheating, and off-topic abuse.

## 12. Functional Requirements

### 12.1 Accounts and Identity

The system must:

- support registration, login, logout, password reset, and session management
- support authenticated user sessions in the website app
- support profile settings and user preferences
- support user-owned game history and replay libraries
- support active-session visibility and security controls

### 12.2 Plans, Billing, and Entitlements

The system must:

- support paid subscription plans
- define feature entitlements by plan
- meter expensive workloads such as replay retention, premium voices, and premium room creation
- gate premium features based on entitlement checks
- expose subscription state to the user interface

The system must not:

- include player-to-player wagering or betting flows in the initial product
- rely on prize-pool or gambling-style mechanics to drive engagement

### 12.3 Chess Index Governance

The system must:

- maintain a public roster of admissible model competitors
- record official source, license, and release metadata for each competitor
- exclude non-compliant or ambiguous models from the default public ladder
- preserve reproducible model identity fields for benchmarking
- support adding new public model releases over time

### 12.4 Match Creation and Lifecycle

The system must:

- create games between two LLMs
- create human-vs-LLM games
- create human-vs-human games with referee support
- support benchmark, showmatch, and interactive modes
- preserve board state through control handoffs
- support replay and export
- keep AI-first play and coaching as the earliest polished product surface before broader social expansions

### 12.5 Deterministic Rules and Illegal Move Handling

The system must:

- validate moves through a deterministic chess engine
- reject illegal moves before board state changes
- emit structured rule-break events
- trigger a referee explanation after deterministic rejection
- request forced correction and resubmission from the responsible player
- log all failed attempts and corrections

### 12.6 Referee Experience

The system must:

- run a dedicated referee model, defaulting to `Gemma 4`
- give the referee access to legal context and engine notifications
- prevent the referee from becoming the source of truth on legality
- allow the referee to explain, mediate, and coach
- support browser-readable and browser-spoken output

### 12.7 Avatar And Personality Experience

The system must:

- let users choose from multiple AI chess personalities
- keep personality, voice, and avatar presentation configurable separately from the gameplay model
- support roles such as coach, rival, announcer, referee, and chaos agent
- allow premium personalities, premium voices, or premium avatar packs as monetizable product surfaces
- support lightweight avatar presentation at launch, such as portraits, reactions, and speaking indicators
- support longer-term user preferences for character tone, coaching style, and voice
- require persona, voice, and avatar concepts to be original and non-infringing
- prohibit real-person imitation or implied endorsement without explicit rights

### 12.8 Coaching And Lesson Experience

The system must:

- support structured lesson tracks over time
- support coach-guided post-game reviews
- support tactic, endgame, and planning drills
- explain moves in idea-centric language rather than only raw engine evaluations
- adapt lesson difficulty to user progress and recurring mistakes
- support tutor-style personas distinct from benchmark competitors and roast-showmatch personalities
- use original lesson architecture, original scripts, and original naming
- avoid copying the lesson structure, trade dress, or branded framing of prior commercial chess products

### 12.9 Showmatch Experience

The system must:

- support banter between players during showmatches
- preserve separation between player chat and referee chat
- support quote-worthy moments, illegal-move callouts, and endgame hype
- allow an optional `Gemma` player preset in showmatches

### 12.10 Interactive Control Handoffs

The system must:

- allow a human to claim a seat midgame
- allow a human to release a seat to an LLM midgame
- display who currently controls each side
- preserve a timestamped control timeline
- ensure replays reflect controller changes accurately

### 12.11 Spectator and Replay Features

The system must:

- stream board state, move list, and chat in real time
- display referee events and correction threads
- provide replay controls
- support bookmarks for highlights such as illegal moves, blunders, swings, and checkmate
- persist transcripts, analysis, and audio references

### 12.12 Community, Moderation, and Fair Play

The system must:

- define and enforce a chess-only community policy
- prohibit politics, harassment, hate, scams, and generic off-topic posting
- support warning, suspension, and ban workflows for repeat low-severity violations
- support immediate action for severe abuse, cheating rings, fraud, threats, or ban evasion
- keep community activity anchored to games, lessons, clubs, and chess discussion
- provide abuse reporting and moderation tooling
- support a fun-loving, welcoming, clearly apolitical community tone

The system must also:

- avoid offering a public gameplay API for rated or live human competition
- support server-authoritative move submission and validation
- support telemetry and review tools for anti-cheat investigation
- distinguish between anti-cheat policy in benchmark, casual, and rated human modes

### 12.13 Ratings and Benchmarking

The system must:

- maintain a public-facing `Chess Index` rating
- support provisional ratings for new entrants
- track win/loss/draw records
- track hallucination and illegal-move rates
- allow engine-anchor benchmarking
- support repeatable comparisons by runtime and hardware class

### 12.14 Model Intake

The system must:

- support discovery of new model releases
- store intake metadata including license and official source
- download official weights or approved reproducible quantizations
- run smoke tests before index admission
- stage new entrants as provisional before full ladder promotion

## 13. UX Requirements

### 13.1 Core Screens

The initial website product should include:

- landing page
- login and registration
- character selection or personality preview surface
- live game page
- replay page
- personal library
- pricing and subscription page
- public `Chess Index` leaderboard
- featured showmatch page
- private room or invite flow
- admin operations surfaces
- lesson and coaching surfaces over time

### 13.2 Live Game Page

The live game page should show:

- board
- move list
- turn and controller state
- player model identities
- current personality identity and avatar presentation
- referee stream
- player banter rail
- user chat input
- engine evaluation panel
- next-line preview panel
- control handoff controls
- premium-state or entitlement warnings when relevant
- fair-play and moderation state when relevant

### 13.3 Replay Page

The replay page should show:

- full move timeline
- board scrubber
- bookmarkable highlights
- transcript and audio alignment
- controller changes over time
- legality events and referee responses

## 14. Data and Logging Requirements

For each game, the system should preserve:

- game metadata
- mode
- participants
- competitor identities
- selected personality, voice, and avatar identifiers where relevant
- prompts
- raw responses
- parsed moves
- legal or illegal outcomes
- referee interventions
- control handoffs
- engine evaluations
- latency and timing
- replay artifacts
- audio artifact references
- moderation actions
- fair-play review metadata

This data must support:

- debugging
- benchmarking
- ratings
- moderation
- user history
- replay generation

## 15. Technical Requirements

### 15.1 Runtime Requirements

- all gameplay-critical model inference must be self-hosted
- initial support exists for `Ollama`
- future support should include `vLLM` and `llama.cpp`
- architecture must preserve runtime abstraction
- rated human competition should not depend on an open public gameplay API

### 15.2 Storage Requirements

- the current MVP uses SQLite
- production should migrate to a relational database suitable for multi-user web workloads
- large artifacts should live in object storage

### 15.3 Realtime Requirements

- live games must stream state changes quickly enough to feel immediate
- event ordering must preserve board truth
- degraded-network states must fail gracefully

### 15.4 Analysis Requirements

- Stockfish should provide evaluation, lookahead, and anchor benchmarking
- the analysis layer must stay separate from the authoritative legality layer

### 15.5 Deployment Requirements

- the paid web product should launch on `Google Cloud Platform`
- the website and stateless app services should target `Cloud Run`
- production relational data should target `Cloud SQL for PostgreSQL`
- replay, audio, and export artifacts should target `Cloud Storage`
- container images should target `Artifact Registry`
- application secrets should target `Secret Manager`
- low-cost GPU-backed inference should start on `Compute Engine Spot VMs`
- the architecture should preserve the option to add `Cloud Run GPU` or larger GPU orchestration later without rewriting the product model

### 15.6 Cost And Cashflow Requirements

- the launch architecture should optimize for low fixed cost and fast iteration
- stateless services should prefer scale-to-zero or low-idle managed services where possible
- long-running or tournament-heavy GPU workloads should prefer discounted compute such as `Compute Engine Spot VMs`
- premium features should be aligned with the real cost of GPU time, storage, replay generation, and voice workloads

## 16. Licensing and Governance Requirements

The public `Chess Index` should:

- default to permissive-license entrants with clearly documented official weights
- prefer official publisher pages as canonical sources
- avoid muddy licensing categories for the baseline public ladder
- track license metadata explicitly
- keep product branding, persona assets, lesson assets, and marketing surfaces original to LexiChess
- prohibit unlicensed trademark, voice, likeness, or trade-dress usage
- require explicit written approval before public claims of endorsement or affiliation

This means the product should distinguish between:

- `allowed in public index`
- `allowed only after legal review`
- `not allowed in public index`

## 17. Success Metrics

### 17.1 Product Metrics

- number of registered users
- number of paying subscribers
- number of games created per week
- number of live matches watched
- replay views per game
- average session duration on live match pages
- games played per personality
- repeat usage of selected characters

### 17.2 Benchmark Metrics

- number of indexed competitors
- time from official model release to provisional index rating
- number of rated games per competitor
- illegal move rate by competitor
- correction success rate by competitor

### 17.3 Reliability Metrics

- match completion rate
- realtime event delivery reliability
- inference failure rate
- referee response latency after illegal move events
- replay generation success rate

### 17.4 Business Metrics

- trial-to-paid conversion
- paid retention
- premium feature usage
- cost per active paid user
- GPU utilization efficiency

## 18. Rollout Plan

### Phase 0: Current State

- backend MVP
- CLI play
- SQLite logging
- Ollama provider
- legality validation

### Phase 1: Benchmark Platform

- model governance and intake metadata
- `Chess Index` ratings foundation
- anchor engine benchmarking
- better exports and replay tooling

### Phase 2: Website Alpha

- auth
- accounts
- first character selection layer
- `GCP` web foundation on `Cloud Run`, `Cloud SQL`, and `Cloud Storage`
- live game page
- replay page
- public leaderboard
- basic subscriptions

### Phase 3: Interactive Product

- human seat claiming
- LLM takeover and human takeover
- private rooms
- personal libraries
- personality preferences and premium voice surfaces

### Phase 4: Showmatch Layer

- `Gemma 4` referee
- player banter
- audio
- richer avatar and character presentation
- featured broadcasts
- highlights and clips

### Phase 5: Scale and Operations

- larger `GCP` and on-prem model fleet
- `20-30` public ladder entrants
- repeatable model intake pipeline
- production operations and moderation

## 19. Risks

### 19.1 Licensing Risk

Open-weight models often have ambiguous or restrictive terms. The public ladder can become legally messy if intake is casual.

Mitigation:

- use explicit admission policy
- record license metadata
- prefer official pages
- require legal review for ambiguous families

### 19.2 Cost Risk

Running many local models, referee flows, audio, and analysis at once can become expensive quickly.

Mitigation:

- tie expensive features to plans
- meter usage
- separate premium from baseline experiences
- use low-fixed-cost managed `GCP` services for the web stack and discounted GPU workers where possible

### 19.3 Product Complexity Risk

LexiChess spans benchmarking, gaming, subscriptions, commentary, moderation, and GPU operations.

Mitigation:

- sequence rollout
- preserve clear boundaries between benchmark and showmatch systems
- keep the MVP slice honest

### 19.4 Reproducibility Risk

Model comparisons can become noisy if quantization, runtime, or hardware are not captured.

Mitigation:

- treat full competitor configuration as the rated identity
- log revision, runtime, and hardware metadata

### 19.5 Tone Risk

Comedy-forward player banter can become repetitive, low-quality, or unsafe.

Mitigation:

- keep referee grounded
- add tone rules and moderation controls
- isolate benchmark mode from showmatch mode

### 19.6 Character Quality Risk

If the character layer feels shallow, repetitive, or cosmetic, users will not build affinity for it and the paid product surface will feel weak.

Mitigation:

- separate gameplay and persona cleanly
- give each character a distinct role and tone
- invest in voice, copy, and reaction quality early
- measure repeat play and attachment to specific personalities

### 19.7 IP And Brand Confusion Risk

If LexiChess is described or designed too closely to legacy chess products, the product can create legal risk and market confusion instead of building its own category.

Mitigation:

- keep product, lesson, persona, voice, and marketing assets original
- add naming, trademark, and content review gates before launch
- avoid implied endorsement or affiliation without explicit written rights
- build a differentiated `LLM-first` story around self-hosted models, live interactivity, and original character systems

## 20. Open Questions

- Which subscription tiers should exist at launch, and which features belong in each one?
- Should private games ever affect public ratings, or should all interactive games stay outside the public ladder?
- Which rating model should be user-facing at launch: Elo only, or Elo plus confidence?
- What is the exact bar for admitting a new model family with unusual license or gating terms?
- Which self-hosted TTS stack is good enough for the first live referee experience?
- Should user-to-player chat be visible to spectators by default, or only in selected public rooms?
- Which personalities should exist at launch, and which ones should be premium?
- What internal naming, brand, and content-review gate should every new public-facing character, lesson, and voice pack pass before release?

## 21. Appendix: Current MVP Reality Check

Today, the repo already includes:

- a Python package in `src/lexichess/`
- command-line game execution
- deterministic move validation via `python-chess`
- SQLite logging
- an `Ollama` provider
- tests around the backend MVP

This PRD describes the product LexiChess is growing toward, while preserving honesty about what exists today.
