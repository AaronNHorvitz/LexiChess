# Contributing to LexiChess

Thank you for your interest in contributing to LexiChess! LexiChess is a Python-based platform for orchestrating LLM chess tournaments, providing AI-driven tutoring, and exposing functionality via a developer API. It aims to advance AI research, chess education, and entertainment, with a goal of becoming a freemium web and mobile app. We welcome contributions from the community to help achieve these goals.

This document outlines how to contribute, including setting up the project, submitting changes, and following our guidelines. Whether you're fixing bugs, adding features, or creating Jupyter notebooks, your contributions are valued!

## How to Contribute

### 1. Getting Started
- **Explore the Project**: Read the [README.md](./README.md) for an overview and the [docs/file_structure.md](./docs/file_structure.md) for the codebase structure.
- **Set Up the Environment**:
  - Clone the repository: `git clone https://github.com/<your-repo>/lexichess.git`
  - Install Python dependencies: `poetry install` (see `pyproject.toml`).
  - Install frontend dependencies: `cd frontend && npm install`.
  - Set up SQLite: Run `scripts/setup_db.py` to initialize the database.
  - (Optional) Install Ollama for local LLMs or configure API keys for Grok/OpenAI (see [Getting Started](./README.md)).
- **Run the Project**:
  - Start the Flask backend: `python src/main.py`.
  - Start the React frontend: `cd frontend && npm run dev`.
  - Explore notebooks: Open `/Notebooks/` in Jupyter (e.g., `jupyter notebook Notebooks/tournament.ipynb`).

### 2. Finding Issues
- Check the [GitHub Issues](https://github.com/<your-repo>/lexichess/issues) for open tasks, bugs, or feature requests.
- Create a new issue if you have a bug report or feature idea, using the provided templates.
- Comment on an issue to express interest in working on it, and coordinate with maintainers.

### 3. Making Changes
- **Fork and Branch**:
  - Fork the repository and clone your fork.
  - Create a feature branch: `git checkout -b feature/your-feature-name`.
- **Develop**: Make changes in the appropriate directory (e.g., `/src/chess` for tournament logic, `/Notebooks` for tutorials).
- **Test**: Add or update tests in `/tests/` and ensure they pass (see [Testing](#testing)).
- **Commit**: Write clear commit messages (e.g., `Add LLM prompt for tutoring feedback in src/tutoring/prompt.py`).
- **Push**: Push your branch to your fork: `git push origin feature/your-feature-name`.
- **Submit a Pull Request**:
  - Open a PR from your fork’s branch to the main repository’s `main` branch.
  - Use the PR template to describe your changes, link to related issues, and note any testing done.
  - Ensure your PR passes automated checks (e.g., linting, tests).

## Code Style
- **Python**:
  - Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) guidelines.
  - Use Black for formatting: `black src/ tests/ scripts/`.
  - Add docstrings for functions and classes (Google style preferred).
- **React/JavaScript**:
  - Use Prettier for formatting: `cd frontend && npm run format`.
  - Follow Airbnb’s [JavaScript Style Guide](https://github.com/airbnb/javascript).
  - Use functional components and hooks.
- **Jupyter Notebooks**:
  - Structure notebooks in `/Notebooks/` with clear markdown headings and comments.
  - Include a brief introduction explaining the notebook’s purpose (e.g., tutorial, analysis).
  - Test notebooks to ensure they run without errors.
- **General**:
  - Keep code modular and aligned with the file structure (see [docs/file_structure.md](./docs/file_structure.md)).
  - Avoid large, monolithic changes; break them into smaller PRs.

## Testing
- **Unit Tests**: Add tests in `/tests/` for new or modified code (e.g., `/tests/chess/test_board.py` for chess logic).
- **Integration Tests**: Ensure features work with the Flask app and SQLite database.
- **Running Tests**: Use `pytest` to run tests: `pytest tests/`.
- **Notebook Tests**: Verify `/Notebooks/` run end-to-end without errors.
- **Requirements**: PRs must include tests for new functionality and pass existing tests.

## Contribution Areas
We encourage contributions in the following areas:
- **Tournaments**: Enhance `/src/chess` (e.g., new time controls, hallucination detection).
- **Tutoring**: Improve `/src/tutoring` (e.g., lesson content, feedback algorithms) or add notebooks in `/Notebooks` (e.g., `tutoring.ipynb`).
- **Web UI**: Build or refine React components in `/frontend/src` (e.g., board visuals, tutoring interface).
- **API**: Develop endpoints in `/src/api` or document them in `/docs/api.md`.
- **Notebooks**: Create or update Jupyter notebooks in `/Notebooks` for tutorials, research, or education.
- **Sandbox**: Experiment with prototypes in `/Sandbox` (e.g., new LLM prompts, API ideas).
- **Documentation**: Update `/docs` (e.g., tutorials, API guides) or improve comments/docstrings.
- **Tests**: Add or improve tests in `/tests/` for better coverage.

## Pull Request Workflow
- **Before Submitting**:
  - Ensure code follows style guidelines (run `black`, `prettier`).
  - Run tests: `pytest tests/`.
  - Update documentation if needed (e.g., `/docs`, notebook intros).
- **PR Guidelines**:
  - Reference related issues (e.g., `Fixes #123`).
  - Describe the change’s purpose and impact.
  - Include tests for new functionality.
  - Keep PRs focused; split large changes into multiple PRs.
- **Automated Checks**:
  - GitHub Actions will run linting (Black, Prettier) and tests.
  - Fix any failing checks before requesting review.
- **Review Process**:
  - Maintainers will review your PR within 3–5 days.
  - Address feedback promptly to keep the PR moving.
  - Once approved, your changes will be merged into `main`.

## Community Guidelines
- Be respectful and inclusive in all interactions (issues, PRs, discussions).
- Provide constructive feedback and ask questions if unclear.
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md) (to be added).

## Questions?
If you have questions or need help, open an issue with the “question” label or reach out in the [Discussions](https://github.com/<your-repo>/lexichess/discussions) tab. We’re excited to have you contribute to LexiChess!