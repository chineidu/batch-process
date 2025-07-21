.PHONY: help type-check format lint lint-fix \
	check all clean format-fix ci-check \
	compose-build compose-watch \
	compose-up compose-down lint-verbose

# Use bash with strict error handling
.SHELLFLAGS := -ec

# Default target when just running "make"
all: format-fix

# ===== ENVIRONMENT VARIABLES =====
COMPOSE_FILE := "docker-compose.yml"

help:
	@echo "Ruff Formatting and Linting Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make type-check       			Run type checking with MyPy"
	@echo "  make format           			Format code using Ruff"
	@echo "  make lint             			Run Ruff linter without fixing issues"
	@echo "  make lint-fix         			Run Ruff linter and fix issues automatically"
	@echo "  make lint-verbose     			Run Ruff linter with verbose output"
	@echo "  make format-fix       			Format code and fix linting issues (one command)"
	@echo "  make check            			Run both formatter and linter without fixing"
	@echo "  make ci-check         			Run all checks for CI (type checking, formatting, linting)"
	@echo "  make worker           			Run worker.py"
	@echo "  make beat           			Run beat (celery beat)"
	@echo "  make flower           			Run flower (task monitoring)"
	@echo "  make producer         			Run producer.py"
	@echo "  make compose-watch    			Watch for changes & rebuild Docker Compose development environment"
	@echo "  make compose-up       			Start Docker Compose development environment"
	@echo "  make compose-down     			Stop Docker Compose development environment"
	@echo "  make compose-down-volumes	 	Stop Docker Compose development environment and remove volumes"
	@echo "  make all              			Same as format-fix (default)"
	@echo "  make clean            			Clean all cache files"
	@echo "  make help             			Show this help message"

# Type checking with MyPy
type-check:
	@echo "Running type checking with MyPy..."
	@bash -c "uv run -m mypy ."
	@echo "Type checking completed."

# Format code with Ruff
format:
	@echo "Formatting code with Ruff..."
	@bash -c "uv run -m ruff format ."

# Lint code with Ruff (no fixing)
lint:
	@echo "Linting code with Ruff..."
	@bash -c "uv run -m ruff check ."

# Lint code with Ruff and fix issues
lint-fix:
	@echo "Linting code with Ruff and applying fixes..."
	@bash -c "uv run -m ruff check --fix ."

# Lint code with Ruff (verbose output)
lint-verbose:
	@echo "Running verbose linting..."
	@bash -c "uv run -m ruff check --verbose ."

# Format and fix in a single command
format-fix: type-check format lint-fix

# Run format and lint without fixing (good for CI)
check:
	@echo "Running full code check (format and lint)..."
	@bash -c "uv run -m ruff format --check ."
	@bash -c "uv run -m ruff check ."

# Complete CI check with type checking
ci-check: type-check check

# ==== Celery commands ====
worker:
	@echo "Running Celery worker..."
	@bash -c "uv run worker.py"

beat:
	@echo "Running Celery beat..."
	@bash -c "uv run celery -A src.celery_pkg.app beat --loglevel=info"

flower:
	# Load environment variables stored in .env
	@set -a && . ./.env && set +a && \
	echo "Running Celery flower..."
	@bash -c "uv run celery -A src.celery_pkg.app flower --basic_auth=$$CELERY_FLOWER_USER:$$CELERY_FLOWER_PASSWORD"

producer:
	@echo "Running Celery producer..."
	@bash -c "uv run main_logic.py"

# ==== Docker Compose commands ====
compose-down:
	@echo "Stopping Docker Compose development environment..."
	docker compose -f ${COMPOSE_FILE} down --remove-orphans && docker image prune -f
	rm -rf ./db/results.db-wal ./db/results.db-shm
	@echo "Docker Compose development environment stopped."

compose-down-volumes:
	@echo "Stopping Docker Compose development environment..."
	docker compose -f ${COMPOSE_FILE} down --remove-orphans --volumes && docker image prune -f
	rm -rf ./db/results.db-wal ./db/results.db-shm
	@echo "Docker Compose development environment stopped."

compose-up: compose-down
	@echo "Starting Docker Compose development environment..."
	docker compose -f ${COMPOSE_FILE} up --build -d
	@echo "Docker Compose development environment started."

compose-watch:
	@echo "Watch for changes and rebuild Docker Compose development environment..."
	docker compose -f ${COMPOSE_FILE} watch
	@echo "Docker Compose development environment started."

# Clean cache files
clean:
	@echo "Cleaning cache files..."
	rm -rf .mypy_cache .ruff_cache __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Cache cleaned."
