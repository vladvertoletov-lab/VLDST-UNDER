#!/bin/sh
set -e

echo "=== VLDST START ==="
echo "PWD=$(pwd)"
echo "=== MIGRATIONS ==="

PYTHONPATH=./backend alembic -c ./backend/alembic.ini upgrade head

echo "=== SEED ==="
PYTHONPATH=./backend python -m app.seed || true

echo "=== BOT ==="
PYTHONPATH=./backend:./bot python ./bot/bot.py &
BOT_PID=$!

echo "=== FASTAPI ==="
PYTHONPATH=./backend exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

kill "$BOT_PID" 2>/dev/null || true
