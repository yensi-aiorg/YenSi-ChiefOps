.PHONY: dev dev-down test test-all lint format clean help

# ── Development ──────────────────────────────────────
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f backend

# ── Testing ──────────────────────────────────────────
test-backend-unit:
	cd backend && python -m pytest tests/unit -v

test-backend-integration:
	cd backend && python -m pytest tests/integration -v

test-backend-all:
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing

test-frontend-unit:
	cd frontend && npm run test:unit

test-frontend-e2e:
	cd frontend && npm run test:e2e

test-all: test-backend-all test-frontend-unit

# ── Linting & Formatting ────────────────────────────
lint-backend:
	cd backend && python -m ruff check app/ && python -m mypy app/ --ignore-missing-imports

lint-frontend:
	cd frontend && npm run lint && npm run typecheck

lint-all: lint-backend lint-frontend

format-backend:
	cd backend && python -m ruff format app/

format-frontend:
	cd frontend && npm run format

format-all: format-backend format-frontend

# ── Cleanup ──────────────────────────────────────────
clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true

# ── Database ─────────────────────────────────────────
seed:
	cd backend && python -m scripts.seed_data

reset-db:
	cd backend && python -m scripts.reset_db

# ── Help ─────────────────────────────────────────────
help:
	@echo "ChiefOps Step Zero - Development Commands"
	@echo ""
	@echo "  make dev              Start all services with hot reload"
	@echo "  make dev-down         Stop dev services"
	@echo "  make up               Start all services (detached)"
	@echo "  make down             Stop all services"
	@echo "  make logs             Follow backend logs"
	@echo ""
	@echo "  make test-all         Run all tests"
	@echo "  make test-backend-all Run backend tests with coverage"
	@echo "  make test-frontend-unit Run frontend unit tests"
	@echo ""
	@echo "  make lint-all         Run all linters"
	@echo "  make format-all       Format all code"
	@echo "  make clean            Stop services and remove volumes"
	@echo ""
	@echo "  make seed             Load sample data"
	@echo "  make reset-db         Clear all database collections"
