# LexiChess

LexiChess is an open-source Python-based platform that orchestrates chess matches between large language models (LLMs), logs gameplay, tracks conversations, and identifies hallucinations (invalid moves or reasoning errors). It also offers interactive chess tutoring through a conversational AI avatar and exposes its functionality via a developer API, making it a powerful tool for AI research, chess education, and entertainment. Built with `python-chess` for game mechanics, SQLite for data storage, and Stockfish for baseline rankings, LexiChess supports API-based LLMs (e.g., ChatGPT, Grok via xAI API) and local LLMs (e.g., LLaMA via Ollama). The project aims to study LLM behavior, teach chess across skill levels, and evolve into a freemium web and mobile app.

## Features
1. **Automated LLM Tournaments**: Runs chess matches between LLMs with tournament-style time controls (e.g., 5+3), logging moves, conversations, and hallucinations for research.
2. **Chess Tutoring**: Delivers interactive lessons (beginner to advanced) via a conversational AI avatar, covering rules, tactics, openings, and strategy with personalized feedback.
3. **Web UI**: Allows human players to compete against LLMs, Stockfish, or other humans, with adjustable difficulty and access to tutoring.
4. **Move Commentary**: Analyzes moves using an open-source opening library (e.g., Lichess database) for real-time insights.
5. **Conversational Avatar**: A human-like AI for tutoring and post-game discussions, supporting text and voice interaction.
6. **Developer API**: Provides programmatic access to tournaments, game data, and tutoring interactions for researchers and developers.
7. **Win Probability Simulations**: Simulates game outcomes to predict win probabilities for research and strategy.

## Tech Stack
- **Core**: Python 3.10+, `python-chess` for chess mechanics and move validation.
- **Database**: SQLite for game states, move logs, conversations, hallucinations, and lesson progress.
- **LLM Integration**:
  - API-based: xAI Grok API, OpenAI API.
  - Local: Ollama for LLaMA or similar models.
- **Chess Engine**: Stockfish for baseline rankings and human vs. AI gameplay.
- **Web UI**: Flask (backend), React with `chessboard.js` (frontend), WebSocket for real-time updates.
- **Tutoring**: ElevenLabs or Mozilla TTS for voice output, Web Speech API for speech-to-text, Three.js for avatar visuals.
- **API**: Flask-RESTful for REST endpoints, OAuth2 or API keys for authentication.
- **Mobile App (Planned)**: React Native for iOS/Android.
- **Time Controls**: Custom Python implementation for tournament rules (e.g., 5+3, 10+0).

## System Requirements
- Python 3.10 or higher.
- SQLite 3.35 or higher.
- Node.js 16+ for frontend development.
- Stockfish 15+ for chess engine integration.
- (Optional) Ollama for local LLM deployment.
- Internet access for API-based LLMs (e.g., Grok, ChatGPT).

## Project Structure
```
lexichess/
├── Notebooks/        # Instructional Jupyter notebooks
├── Sandbox/          # Development space for experiments
├── src/              # Backend Python code (chess, LLM, tutoring, API)
├── frontend/         # React frontend for web UI
├── docs/             # Documentation and diagrams
├── tests/            # Unit and integration tests
├── scripts/          # Utility scripts
├── README.md         # Project overview
├── CONTRIBUTING.md   # Contribution guidelines
├── LICENSE           # MIT license
└── pyproject.toml    # Python dependencies
```

For a detailed file structure, including a visual diagram, see [docs/file_structure.md](./docs/file_structure.md).

## Project Goals
- **Research**: Study LLM reasoning, hallucinations, and teaching effectiveness in chess.
- **Education**: Provide AI-driven chess tutoring for beginners to advanced players.
- **Entertainment**: Offer engaging human-AI chess matches and LLM tournaments.
- **Developer Ecosystem**: Enable third-party integrations via a robust API.
- **Productization**: Develop a freemium web/mobile app with premium features like advanced tutoring, analytics, and API access.

## Getting Started
(TODO: Add detailed installation instructions, including `pip install`, environment setup, and API key configuration once core components are implemented.)

## Contributing
Contributions are welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on code style, issue reporting, and pull requests. We encourage contributions to tournament logic, tutoring content, UI enhancements, API endpoints, and Jupyter notebooks.

## License
MIT License. Commercial productization may involve dual-licensing for premium features or API access.

## Roadmap
1. **Phase 1 (3–6 months)**: Implement LLM tournament system with hallucination tracking, time controls, and SQLite logging.
   - Deliverables: Tournament manager, Stockfish integration, research logs.
2. **Phase 2 (6–12 months)**: Develop web UI for human vs. LLM/Stockfish play and initial text-based tutoring interface.
   - Deliverables: Flask/React UI, `chessboard.js` board, difficulty settings, basic tutoring.
3. **Phase 3 (3–5 months)**: Integrate open-source opening library for move commentary.
   - Deliverables: Commentary engine, UI integration.
4. **Phase 4 (6–12 months)**: Build conversational avatar with full tutoring system, including voice and visual components.
   - Deliverables: Lesson curriculum, TTS/speech-to-text, 2D/3D avatar.
5. **Phase 5 (3–6 months)**: Develop developer API for programmatic access to tournaments, game data, and tutoring interactions.
   - Deliverables: RESTful endpoints, API documentation, authentication system.
6. **Phase 6 (6 months)**: Add win probability simulations for research and strategy insights.
   - Deliverables: Simulation engine, UI visualizations.
7. **Phase 7 (12–18 months)**: Launch mobile app and finalize freemium product with monetization.
   - Deliverables: React Native app, payment integration, premium features.