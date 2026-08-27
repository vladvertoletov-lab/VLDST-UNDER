#!/bin/sh
set -e

echo "=== VLDST START ==="

echo "=== MIGRATIONS ==="
cd backend
PYTHONPATH="$PWD" alembic -c alembic.ini upgrade head

echo "=== SEED ==="
PYTHONPATH="$PWD" python -m app.seed

echo "=== BOT ==="
cd ..
PYTHONPATH="$PWD/backend:$PWD/bot" python bot/bot.py &
BOT_PID=$!

echo "=== FASTAPI ==="
PYTHONPATH="$PWD/backend" exec uvicorn app.main:app --host 0.0.0.0 --port 8000

kill "$BOT_PID" 2>/dev/null || true
