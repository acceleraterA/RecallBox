#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Checking backend imports..."
(
  cd "$ROOT_DIR/backend"
  if [[ ! -d .venv ]]; then
    python3 -m venv .venv
  fi
  . .venv/bin/activate
  pip install -r requirements.txt
  PYTHONDONTWRITEBYTECODE=1 python -c 'import app.main; import app.backfill_embeddings; import app.backfill_rag; print("backend imports ok")'
)

echo "Checking frontend..."
(
  cd "$ROOT_DIR/frontend"
  npm install
  npm run lint
  npm run build
)

echo "All checks passed."
