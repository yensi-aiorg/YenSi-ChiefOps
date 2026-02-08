.PHONY: infra infra-down backend setup logs test-all lint-all format-all clean help

# ── Quick Start ─────────────────────────────────────
# 1. make setup       (one-time: create venv + install deps)
# 2. cp .env.example .env
# 3. make infra       (start frontend + mongo + redis in Docker)
# 4. make backend     (separate terminal: start backend on host)

# ── Infrastructure (Docker) ─────────────────────────
infra:
	docker compose up --build -d

infra-down:
	docker compose down

logs:
	docker compose logs -f

logs-frontend:
	docker compose logs -f frontend

# ── Backend (Host) ──────────────────────────────────
backend:
	bash scripts/dev.sh

setup:
	bash scripts/setup.sh

# ── Testing ─────────────────────────────────────────
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

# ── Linting & Formatting ───────────────────────────
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

# ── Cleanup ─────────────────────────────────────────
clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true

# ── Database ────────────────────────────────────────
seed:
	cd backend && python -m scripts.seed_data

reset-db:
	cd backend && python -m scripts.reset_db

# ── Help ────────────────────────────────────────────
help:
	@echo "ChiefOps — Local Dev Commands"
	@echo ""
	@echo "  Quick Start:"
	@echo "    make setup          One-time: create venv + install deps"
	@echo "    make infra          Start Docker services (frontend + mongo + redis)"
	@echo "    make backend        Start backend on host (uvicorn, separate terminal)"
	@echo ""
	@echo "  Infrastructure:"
	@echo "    make infra-down     Stop Docker services"
	@echo "    make logs           Follow all Docker logs"
	@echo "    make logs-frontend  Follow frontend logs"
	@echo ""
	@echo "  Testing:"
	@echo "    make test-all       Run all tests"
	@echo "    make test-backend-all  Backend tests with coverage"
	@echo "    make test-frontend-unit  Frontend unit tests"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make lint-all       Run all linters"
	@echo "    make format-all     Format all code"
	@echo "    make clean          Stop services + remove volumes + caches"
	@echo ""
	@echo "  Database:"
	@echo "    make seed           Load sample data"
	@echo "    make reset-db       Clear all collections"
