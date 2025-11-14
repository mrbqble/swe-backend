.PHONY: venv install run dev test lint fmt fmt-check migrate revision seed precommit

PYTHON ?= python
POETRY ?= poetry
ALEMBIC = $(POETRY) run alembic -c alembic.ini

venv:
	$(POETRY) env use $(PYTHON)

install:
	$(POETRY) install

run:
	$(POETRY) run uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	$(POETRY) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(POETRY) run pytest

lint:
	$(POETRY) run ruff check .
	$(POETRY) run mypy app

fmt:
	$(POETRY) run black app tests
	$(POETRY) run isort app tests

fmt-check:
	$(POETRY) run black --check app tests
	$(POETRY) run isort --check-only app tests

migrate:
	$(ALEMBIC) upgrade head

revision:
	@if [ -z "$(name)" ]; then echo "Usage: make revision name=your_message" && exit 1; fi
	$(ALEMBIC) revision --autogenerate -m "$(name)"

seed:
	$(POETRY) run python -m app.scripts.seed

precommit:
	$(POETRY) run pre-commit run --all-files

compose:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f api db

