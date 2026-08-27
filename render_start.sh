#!/bin/sh
set -e

echo "=== VLDST START ==="

echo "=== MIGRATIONS ==="
cd /app/backend
PYTHONPATH=/app/backend alembic -c /app/backend/alembic.ini upgrade head

echo "=== SEED ==="
PYTHONPATH=/app/backend python -m app.seed || true

echo "=== BOT ==="
cd /app
PYTHONPATH=/app/backend:/app/bot python /app/bot/bot.py &
BOT_PID=$!

echo "=== FASTAPI ==="
PYTHONPATH=/app/backend exec uvicorn app.main:app --host 0.0.0.0 --port 8000
