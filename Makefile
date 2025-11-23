# ==============================================================================
# Makefile for B2B Supplier-Wholesale Exchange Platform
# ==============================================================================
# This Makefile provides convenient commands for common development tasks.
#
# Usage:
#   make help          # Show all available commands
#   make install       # Install dependencies
#   make dev           # Run development server
#
# Note: On Windows, you may need to use WSL, Git Bash, or the provided
#       scripts.ps1 / scripts.bat files instead of Make.
# ==============================================================================

# Default target
.DEFAULT_GOAL := help

# Phony targets (targets that don't create files)
.PHONY: help install install-dev dev start lint lint-fix format type-check check clean \
	migrate revision upgrade downgrade \
	docker-build docker-up docker-down docker-logs docker-shell docker-restart docker-clean \
	setup-env pre-commit-run pre-commit-update

# ==============================================================================
# Help
# ==============================================================================

help: ## Show this help message
	@echo "╔══════════════════════════════════════════════════════════════════════════════╗"
	@echo "║                    Available Make Commands                                    ║"
	@echo "╚══════════════════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 Setup & Installation:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(install|setup)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🚀 Development:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(dev|start)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🔍 Code Quality:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(lint|format|type-check|check|pre-commit)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🗄️  Database:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(migrate|revision|upgrade|downgrade)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🐳 Docker:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E 'docker' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🧹 Maintenance:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(clean|setup-env)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ==============================================================================
# Setup & Installation
# ==============================================================================

install: ## Install production dependencies
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

install-dev: install ## Install dependencies and setup development tools
	@echo "🔧 Setting up pre-commit hooks..."
	pre-commit install
	@echo "✅ Development environment ready!"

setup-env: ## Create .env file from env.example if it doesn't exist
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env file from env.example..."; \
		cp env.example .env; \
		echo "✅ .env file created. Please edit it with your settings."; \
	else \
		echo "⚠️  .env file already exists. Skipping..."; \
	fi

# ==============================================================================
# Development Server
# ==============================================================================

dev: ## Run the development server with hot reload
	@echo "🚀 Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

start: ## Run the production server
	@echo "🚀 Starting production server..."
	uvicorn app.main:app --host 0.0.0.0 --port 8000

# ==============================================================================
# Code Quality
# ==============================================================================

format: ## Format code with ruff
	@echo "✨ Formatting code..."
	ruff format app

format-check: ## Check if code is formatted (CI use)
	@echo "🔍 Checking code formatting..."
	ruff format --check app

lint: ## Run linter (ruff check)
	@echo "🔍 Running linter..."
	ruff check app

lint-fix: ## Run linter and automatically fix issues
	@echo "🔧 Running linter and fixing issues..."
	ruff check --fix app

type-check: ## Run type checker (mypy)
	@echo "🔍 Running type checker..."
	mypy app

security: ## Run security linting (bandit)
	@echo "🔒 Running security linting..."
	bandit -r app -f json -o bandit-report.json || true
	bandit -r app -ll
	@echo "✅ Security check complete! See bandit-report.json for details."

check: lint lint-fix format-check format type-check security ## Run all checks (lint, type-check, security)
	@echo "✅ All checks passed!"

ci: lint security ## Run CI-like checks (lint + security)
	@echo "✅ CI checks passed!"

export-openapi: ## Export OpenAPI schema to docs/openapi.json
	@echo "📥 Exporting OpenAPI schema..."
	@python scripts/export_openapi.py --url http://localhost:8000 --output docs/openapi.json

demo: ## Run demo script (requires API running)
	@echo "🎬 Running demo script..."
	@bash scripts/demo.sh

check-dod: ## Run Definition of Done verification
	@echo "🔍 Running DoD verification..."
	@python scripts/check_dod.py

pre-commit-run: ## Run pre-commit hooks on all files
	@echo "🔍 Running pre-commit hooks..."
	pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	@echo "🔄 Updating pre-commit hooks..."
	pre-commit autoupdate

# ==============================================================================
# Database Migrations
# ==============================================================================

migrate: ## Create a new migration (usage: make migrate MESSAGE="description")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "❌ Error: MESSAGE parameter is required"; \
		echo "Usage: make migrate MESSAGE=\"your migration description\""; \
		exit 1; \
	fi
	@echo "📝 Creating migration: $(MESSAGE)"
	alembic revision --autogenerate -m "$(MESSAGE)"

revision: migrate ## Alias for migrate (create a new migration)

upgrade: ## Apply all pending database migrations
	@echo "⬆️  Applying database migrations..."
	alembic upgrade head

downgrade: ## Rollback one migration
	@echo "⬇️  Rolling back one migration..."
	alembic downgrade -1

downgrade-base: ## Rollback all migrations (⚠️  DANGEROUS)
	@echo "⚠️  WARNING: This will rollback all migrations!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		alembic downgrade base; \
	else \
		echo "Cancelled."; \
	fi

migration-history: ## Show migration history
	@echo "📜 Migration history:"
	alembic history

current-revision: ## Show current database revision
	@echo "📍 Current database revision:"
	alembic current


# ==============================================================================
# Docker Commands
# ==============================================================================

docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t swe-backend:latest .

docker-up: ## Start services with Docker Compose
	@echo "🐳 Starting Docker Compose services..."
	docker-compose up -d
	@echo "✅ Services started. Use 'make docker-logs' to view logs."

docker-down: ## Stop Docker Compose services
	@echo "🐳 Stopping Docker Compose services..."
	docker-compose down

docker-restart: docker-down docker-up ## Restart Docker Compose services

docker-logs: ## View Docker Compose logs (follow mode)
	@echo "📋 Viewing Docker Compose logs (Ctrl+C to exit)..."
	docker-compose logs -f

docker-logs-app: ## View application logs only
	@echo "📋 Viewing application logs..."
	docker-compose logs -f app

docker-logs-db: ## View database logs only
	@echo "📋 Viewing database logs..."
	docker-compose logs -f db

docker-shell: ## Open interactive shell in application container
	@echo "🐚 Opening shell in application container..."
	docker-compose exec app bash

docker-shell-db: ## Open PostgreSQL shell in database container
	@echo "🐚 Opening PostgreSQL shell..."
	docker-compose exec db psql -U postgres -d mydb

docker-clean: ## Remove containers, volumes, and images
	@echo "🧹 Cleaning up Docker resources..."
	@echo "⚠️  WARNING: This will remove containers, volumes, and images!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --rmi all; \
		echo "✅ Docker resources cleaned."; \
	else \
		echo "Cancelled."; \
	fi

docker-rebuild: docker-down docker-build docker-up ## Rebuild and restart Docker services

# ==============================================================================
# Maintenance
# ==============================================================================

clean: ## Clean cache files and build artifacts
	@echo "🧹 Cleaning cache and build files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build dist *.egg-info .eggs 2>/dev/null || true
	@rm -rf .tox .nox 2>/dev/null || true
	@echo "✅ Cleanup complete!"

clean-all: clean ## Clean everything including logs and virtual environment
	@echo "🧹 Deep cleaning..."
	@rm -rf logs/*.log 2>/dev/null || true
	@rm -rf .venv venv env 2>/dev/null || true
	@echo "✅ Deep cleanup complete!"

# ==============================================================================
# Utility Commands
# ==============================================================================

requirements: ## Update requirements.txt from current environment
	@echo "📦 Updating requirements.txt..."
	@pip freeze > requirements.txt
	@echo "✅ requirements.txt updated"

version: ## Show application version
	@python -c "from app.core.config import settings; print(f'Version: {settings.VERSION}')"

info: ## Show project information
	@echo "╔══════════════════════════════════════════════════════════════════════════════╗"
	@echo "║                    Project Information                                        ║"
	@echo "╚══════════════════════════════════════════════════════════════════════════════╝"
	@python -c "from app.core.config import settings; \
		print(f'Project: {settings.PROJECT_NAME}'); \
		print(f'Version: {settings.VERSION}'); \
		print(f'Environment: {settings.ENV}'); \
		print(f'API Prefix: {settings.API_V1_PREFIX}')"
	@echo ""
	@echo "Python version:"
	@python --version
	@echo ""
	@echo "Installed packages:"
	@pip list | head -10
