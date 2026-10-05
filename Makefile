# Agent Configurator: common tasks. `make help` lists them.
# Prefer the Python versions the project is tested on; fall back to python3.
PY ?= $(shell command -v python3.12 || command -v python3.13 || command -v python3)
VENV := .venv
BIN := $(VENV)/bin

.PHONY: help setup api web dev test lint check golden catalog examples verify-examples up down clean

help:
	@grep -E '^[a-z-]+:.*?## ' Makefile | awk -F':.*?## ' '{printf "  \033[1m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Install the engine (Python venv) and the web app (npm)
	test -d $(VENV) || $(PY) -m venv $(VENV)
	$(BIN)/pip install -q --upgrade pip
	$(BIN)/pip install -q -e ".[api,dev]"
	cd apps/web && npm install --no-audit --no-fund
	@echo "\nReady. Run: make dev   (then open http://localhost:3210)"

api: ## Run the engine API on :8787 (auto-reload)
	$(BIN)/uvicorn configurator_api.main:app --port 8787 --reload --reload-dir packages --reload-dir apps/api --reload-dir modules

web: ## Run the canvas on :3210
	cd apps/web && npm run dev

dev: ## Run engine + canvas together (Ctrl+C stops both)
	@$(MAKE) -j2 api web

test: ## Engine tests: schema, rules, golden files, CLI, API, AI router (mocked)
	$(BIN)/pytest

lint: ## Ruff + mypy for the engine, ESLint + tsc for the canvas
	$(BIN)/ruff check packages apps/api tests scripts examples/build_examples.py
	$(BIN)/mypy
	cd apps/web && npm run -s lint && npm run -s typecheck

check: lint test ## Everything CI runs on every push (except the export matrix)

golden: ## Re-record golden files after an intended template change
	$(BIN)/python scripts/update_golden.py

catalog: ## Rebuild blueprints and the canvas catalog snapshot
	$(BIN)/python examples/build_examples.py
	$(BIN)/python scripts/export_catalog.py

examples: ## Render the three reference exports into examples/exports/
	rm -rf examples/exports
	for b in docs-qa support-bot research-team; do $(BIN)/configurator generate examples/specs/$$b.json -o examples/exports/$$b > /dev/null; done
	@echo "Wrote examples/exports/{docs-qa,support-bot,research-team}"

verify-examples: ## Render every blueprint and run each export's own ruff, mypy and tests
	$(BIN)/python scripts/verify_matrix.py

up: ## Run the configurator itself with Docker Compose (API + canvas)
	docker compose up --build

down: ## Stop Docker Compose
	docker compose down

clean: ## Remove build artefacts
	rm -rf apps/web/.next .pytest_cache .mypy_cache .ruff_cache
