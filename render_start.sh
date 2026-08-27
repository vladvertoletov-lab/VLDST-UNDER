#!/bin/sh
set -e

echo "=== VLDST START ==="

echo "=== MIGRATIONS ==="
PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head

echo "=== SEED ==="
PYTHONPATH=backend python -m app.seed

echo "=== START BOT ==="
PYTHONPATH=backend:bot python bot/bot.py &
BOT_PID=$!

cleanup() {
    kill "$BOT_PID" 2>/dev/null || true
    wait "$BOT_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "=== START WEB ==="
PYTHONPATH=backend uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
WEB_PID=$!

wait "$WEB_PID"
