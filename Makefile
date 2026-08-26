BACKEND_DIR := backend
FRONTEND_DIR := frontend
PYTHON_BIN := $(BACKEND_DIR)/.venv/bin

.PHONY: help install dev-backend dev-frontend lint lint-backend lint-frontend \
	typecheck format format-check test test-backend build db-up migrate

help:
	@printf '%s\n' \
		'install        Install backend and frontend dependencies' \
		'dev-backend    Start the FastAPI development server' \
		'dev-frontend   Start the Vite development server' \
		'lint           Run backend and frontend linters' \
		'typecheck      Run backend type checking' \
		'format         Format configured source code' \
		'format-check   Check configured source formatting' \
		'test           Run backend tests' \
		'build          Build the frontend for production' \
		'db-up          Start local services from Docker Compose' \
		'migrate        Apply database migrations'

install:
	uv sync --project $(BACKEND_DIR)
	npm --prefix $(FRONTEND_DIR) ci

dev-backend:
	$(PYTHON_BIN)/fastapi dev $(BACKEND_DIR)/app/main.py

dev-frontend:
	npm --prefix $(FRONTEND_DIR) run dev

lint: lint-backend lint-frontend

lint-backend:
	$(PYTHON_BIN)/ruff check $(BACKEND_DIR)

lint-frontend:
	npm --prefix $(FRONTEND_DIR) run lint

typecheck:
	$(PYTHON_BIN)/mypy $(BACKEND_DIR)/app $(BACKEND_DIR)/tests

format:
	$(PYTHON_BIN)/ruff format $(BACKEND_DIR)

format-check:
	$(PYTHON_BIN)/ruff format --check $(BACKEND_DIR)

test: test-backend

test-backend:
	$(PYTHON_BIN)/pytest $(BACKEND_DIR)

build:
	npm --prefix $(FRONTEND_DIR) run build

db-up:
	@if [ ! -f docker-compose.yml ]; then \
		echo 'Docker Compose is not configured yet (planned in F-003).'; \
		exit 1; \
	fi
	docker compose up -d

migrate:
	@if [ ! -d $(BACKEND_DIR)/alembic ]; then \
		echo 'Database migrations are not configured yet (planned in F-004).'; \
		exit 1; \
	fi
	$(PYTHON_BIN)/alembic -c $(BACKEND_DIR)/alembic.ini upgrade head
