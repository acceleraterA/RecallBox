#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting local Postgres..."
docker compose up -d postgres

echo "Preparing backend..."
if [[ ! -d backend/.venv ]]; then
  python3 -m venv backend/.venv
fi
if [[ ! -f backend/.env ]]; then
  cp backend/.env.example backend/.env
fi
(
  cd backend
  . .venv/bin/activate
  pip install -r requirements.txt
  alembic upgrade head
)

echo "Preparing frontend..."
if [[ ! -f frontend/.env.local ]]; then
  cp frontend/.env.example frontend/.env.local
fi
if [[ ! -d frontend/node_modules ]]; then
  (cd frontend && npm install)
fi

echo "Starting FastAPI on http://localhost:8000"
(
  cd backend
  . .venv/bin/activate
  uvicorn app.main:app --reload --port 8000
) &
BACKEND_PID=$!

echo "Starting Next.js on http://localhost:3000"
(
  cd frontend
  npm run dev
) &
FRONTEND_PID=$!

echo
echo "RecallBox is starting:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop backend and frontend."

wait -n "$BACKEND_PID" "$FRONTEND_PID"
