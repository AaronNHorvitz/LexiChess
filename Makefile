PYTHON ?= python3
VENV ?= .venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PYTEST := $(VENV_BIN)/pytest
RUFF := $(VENV_BIN)/ruff
MYPY := $(VENV_BIN)/mypy
PRE_COMMIT := $(VENV_BIN)/pre-commit
PYTHONPATH_SRC := PYTHONPATH=src

.PHONY: bootstrap install install-dev validate-env lint format test coverage typecheck smoke pre-commit

bootstrap:
	scripts/bootstrap.sh

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e '.[dev]'

validate-env:
	$(PYTHONPATH_SRC) $(VENV_BIN)/python scripts/validate_env.py

lint:
	$(RUFF) check src tests scripts

format:
	$(RUFF) format src tests scripts
	$(VENV_BIN)/black src tests scripts

test:
	$(PYTHONPATH_SRC) $(PYTEST)

coverage:
	$(PYTHONPATH_SRC) $(PYTEST) --cov=src/lexichess --cov-report=term-missing

typecheck:
	$(PYTHONPATH_SRC) $(MYPY) src/lexichess

smoke:
	scripts/smoke_test.sh

pre-commit:
	$(PRE_COMMIT) run --all-files
