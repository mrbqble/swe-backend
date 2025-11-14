# SCP API Scaffold

Minimal FastAPI project structure for the Supplier–Consumer Platform backend.

## Quickstart
```bash
poetry run uvicorn app.main:app --reload --env-file .env
```
Then open http://localhost:8000/health to verify the service returns `{ "status": "ok" }`.

## Database migrations
Using Alembic directly:
```bash
poetry run alembic -c alembic.ini revision -m "init"
poetry run alembic -c alembic.ini upgrade head
```

With Makefile helpers:
```bash
make revision name="init"
make migrate
```

## Testing
```bash
poetry run pytest -q
```

## Environment
Duplicate `.env.example` as `.env` and adjust values for local development.
```
cp .env.example .env
```
