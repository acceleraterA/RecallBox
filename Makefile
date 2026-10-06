SHELL := /bin/bash

.PHONY: help install backend-install frontend-install db db-stop migrate backend frontend dev check backfill-embeddings backfill-rag

help:
	@echo "RecallBox commands"
	@echo "  make install             Install backend and frontend dependencies"
	@echo "  make db                  Start local Postgres"
	@echo "  make migrate             Run backend migrations"
	@echo "  make backend             Start FastAPI on http://localhost:8000"
	@echo "  make frontend            Start Next.js on http://localhost:3000"
	@echo "  make dev                 Start Postgres, backend, and frontend"
	@echo "  make check               Run local backend/frontend checks"
	@echo "  make backfill-embeddings Backfill item-level embeddings"
	@echo "  make backfill-rag        Backfill RAG chunks"

install: backend-install frontend-install

backend-install:
	cd backend && test -d .venv || python3 -m venv .venv
	cd backend && . .venv/bin/activate && pip install -r requirements.txt
	cd backend && test -f .env || cp .env.example .env

frontend-install:
	cd frontend && npm install
	cd frontend && test -f .env.local || cp .env.example .env.local

db:
	docker compose up -d postgres

db-stop:
	docker compose stop postgres

migrate:
	cd backend && . .venv/bin/activate && alembic upgrade head

backend: backend-install migrate
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

frontend: frontend-install
	cd frontend && npm run dev

dev:
	./scripts/dev.sh

check:
	./scripts/check.sh

backfill-embeddings:
	cd backend && . .venv/bin/activate && python -m app.backfill_embeddings

backfill-rag:
	cd backend && . .venv/bin/activate && python -m app.backfill_rag --limit 3
