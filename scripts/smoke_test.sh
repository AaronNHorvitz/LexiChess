#!/usr/bin/env bash

set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv}"
PYTHON="${VENV_DIR}/bin/python"

PYTHONPATH=src "${PYTHON}" scripts/validate_env.py
PYTHONPATH=src "${PYTHON}" -m lexichess.cli --help >/dev/null
PYTHONPATH=src "${PYTHON}" - <<'PY'
from lexichess.config import AppSettings

settings = AppSettings.from_env(env={}, dotenv_path=None)
assert settings.default_provider.value == "ollama"
assert settings.max_plies > 0
print("Smoke test passed.")
PY
