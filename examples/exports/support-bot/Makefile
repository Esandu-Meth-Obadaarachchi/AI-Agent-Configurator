# support-bot: common tasks. Run `make help` to list them.
# Prefer the Python versions this project is tested on; fall back to python3.
PY ?= $(shell command -v python3.12 || command -v python3.13 || command -v python3)
.PHONY: help setup dev api ui test lint up down db ingest

help:
	@grep -E '^[a-z]+:.*?## ' Makefile | awk -F':.*?## ' '{printf "  %-8s %s\n", $$1, $$2}'

setup: ## Install backend and frontend dependencies and create .env
	test -f .env || cp .env.example .env
	cd backend && $(PY) -m venv .venv && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

db: ## Start only Postgres (for local development)
	docker compose up -d postgres

api: ## Run the API with auto-reload on http://localhost:8000
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

ui: ## Run the chat UI on http://localhost:3000
	cd frontend && npm run dev -- --port 3000

dev: ## Run API and UI together (Ctrl+C stops both)
	docker compose up -d postgres
	$(MAKE) -j2 api ui

test: ## Run the backend tests (offline demo model, no API key needed)
	cd backend && .venv/bin/pytest

lint: ## Lint and type-check
	cd backend && .venv/bin/ruff check . && .venv/bin/mypy app
	cd frontend && npm run lint && npm run typecheck

ingest: ## Load backend/data/docs into the knowledge base
	cd backend && .venv/bin/python -m app.rag.ingest helpdocs data/docs

up: ## Build and start everything with Docker Compose
	docker compose up --build

down: ## Stop Docker Compose
	docker compose down
