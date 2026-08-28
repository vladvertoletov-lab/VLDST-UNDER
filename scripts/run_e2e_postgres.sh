#!/usr/bin/env bash
set -euo pipefail
: "${E2E_DATABASE_URL:?Set E2E_DATABASE_URL=postgresql+asyncpg://...}"
export PYTHONPATH="$(pwd)/backend:${PYTHONPATH:-}"
python -m alembic -c backend/alembic.ini upgrade head
python -m app.seed
pytest -q tests/test_e2e_postgres.py
