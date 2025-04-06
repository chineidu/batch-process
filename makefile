.PHONY: help type-check format lint lint-fix check all clean format-fix ci-check lint-verbose

# Use bash with strict error handling
.SHELLFLAGS := -ec

# Default target when just running "make"
all: format-fix

help:
	@echo "Ruff Formatting and Linting Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make type-check    Run type checking with MyPy"
	@echo "  make format        Format code using Ruff"
	@echo "  make lint          Run Ruff linter without fixing issues"
	@echo "  make lint-fix      Run Ruff linter and fix issues automatically"
	@echo "  make lint-verbose  Run Ruff linter with verbose output"
	@echo "  make format-fix    Format code and fix linting issues (one command)"
	@echo "  make check         Run both formatter and linter without fixing"
	@echo "  make ci-check      Run all checks for CI (type checking, formatting, linting)"
	@echo "  make all           Same as format-fix (default)"
	@echo "  make clean         Clean all cache files"
	@echo "  make help          Show this help message"

# Type checking with MyPy
type-check:
	@echo "Running type checking with MyPy..."
	@python -m mypy .
	@echo "Type checking completed."

# Format code with Ruff
format:
	@echo "Formatting code with Ruff..."
	@python -m ruff format .

# Lint code with Ruff (no fixing)
lint:
	@echo "Linting code with Ruff..."
	@python -m ruff check .

# Lint code with Ruff and fix issues
lint-fix:
	@echo "Linting code with Ruff and applying fixes..."
	@python -m ruff check --fix .

# Lint code with Ruff (verbose output)
lint-verbose:
	@echo "Running verbose linting..."
	@python -m ruff check --verbose .

# Format and fix in a single command
format-fix: type-check format lint-fix

# Run format and lint without fixing (good for CI)
check:
	@echo "Running full code check (format and lint)..."
	@python -m ruff format --check .
	@python -m ruff check .

# Complete CI check with type checking
ci-check: type-check check

# Clean cache files
clean:
	@echo "Cleaning cache files..."
	rm -rf .mypy_cache .ruff_cache __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "Cache cleaned."