# SCP API Scaffold

Minimal FastAPI project structure for the Supplier–Consumer Platform backend.

## Prerequisites
- Python 3.11+
- [Poetry](https://python-poetry.org/)
- Docker & Docker Compose (optional but recommended)

## Environment setup
1. Copy the sample env and adjust values as needed:
   ```bash
   cp .env.example .env
   ```
   Change `APP_ENV` to `dev`, `test`, or `prod` to switch environments. The service reads these via `pydantic-settings`.

2. Install dependencies:
   ```bash
   poetry install
   ```

## Common workflows (Make targets)

### Fresh start
```bash
make down    # stops containers and removes volumes if previously running
make compose # builds images and starts postgres + api (with reload)
make migrate # runs alembic upgrade head
make seed    # inserts demo data (owner, supplier, consumer, products)
```
Visit http://localhost:8000/health to verify the API returns the status payload with DB connectivity.

### Local development server (without Docker)
```bash
poetry run uvicorn app.main:app --reload
```

### Create a new Alembic revision after changing models
```bash
make revision name="short_description"
```
Edit the generated script under `app/db/migrations/versions/` as needed, then apply with `make migrate`.

### Quality & tests
```bash
make fmt   # runs black + isort
make lint  # runs ruff + mypy
make test  # runs pytest with coverage summary
```
You can run `make lint && make test` for a CI-style verification.

### Tear down
```bash
make down   # removes services and volumes
```

## Docker-only workflow
```bash
make compose          # start services (api hot-reloads on source change)
make migrate
make seed
make logs             # follow container logs (api + db)
```

## Health endpoint
```bash
curl http://localhost:8000/health
# {
#   "status": "ok",
#   "env": "dev",
#   "version": "0.1.0",
#   "db": "ok"
# }
```
