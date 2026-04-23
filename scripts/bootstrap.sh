#!/usr/bin/env bash

set -euo pipefail

VENV_DIR="${VENV_DIR:-.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

"${PYTHON_BIN}" -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/pip" install -e '.[dev]'
"${VENV_DIR}/bin/pre-commit" install

echo "LexiChess bootstrap complete."
