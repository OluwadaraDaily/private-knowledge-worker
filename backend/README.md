# Backend

FastAPI backend for Private Knowledge Worker.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)

## Run locally

```bash
uv sync
uv run fastapi dev
```

The API information endpoint is available at <http://127.0.0.1:8000/api/v1/> and the interactive API documentation at <http://127.0.0.1:8000/docs>.

## Quality checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

To apply formatting changes, run `uv run ruff format .`.

## Isolated test database

Set `TEST_DATABASE_URL` to a separate PostgreSQL database before running database
integration tests. The application database and test database URLs must differ.
Apply the schema to that database with:

```bash
export TEST_DATABASE_URL=postgresql+psycopg://pkw:change-me@127.0.0.1:5432/private_knowledge_worker_test
DATABASE_URL="$TEST_DATABASE_URL" uv run alembic upgrade head
```
