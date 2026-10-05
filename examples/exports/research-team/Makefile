# research-team: common tasks. Run `make help` to list them.
.PHONY: help setup dev api ui test lint up down

help:
	@grep -E '^[a-z]+:.*?## ' Makefile | awk -F':.*?## ' '{printf "  %-8s %s\n", $$1, $$2}'

setup: ## Install backend and frontend dependencies and create .env
	test -f .env || cp .env.example .env
	cd backend && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

api: ## Run the API with auto-reload on http://localhost:8000
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

ui: ## Run the chat UI on http://localhost:3000
	cd frontend && npm run dev -- --port 3000

dev: ## Run API and UI together (Ctrl+C stops both)
	$(MAKE) -j2 api ui

test: ## Run the backend tests (offline demo model, no API key needed)
	cd backend && .venv/bin/pytest

lint: ## Lint and type-check
	cd backend && .venv/bin/ruff check . && .venv/bin/mypy app
	cd frontend && npm run lint && npm run typecheck

up: ## Build and start everything with Docker Compose
	docker compose up --build

down: ## Stop Docker Compose
	docker compose down
