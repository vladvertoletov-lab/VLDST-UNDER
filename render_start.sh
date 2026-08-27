#!/bin/sh
set -e

echo "=== VLDST START ==="

echo "=== MIGRATIONS ==="
cd backend
alembic -c alembic.ini upgrade head

echo "=== SEED ==="
PYTHONPATH=. python -m app.seed

echo "=== BOT ==="
cd ..
PYTHONPATH=backend:bot python bot/bot.py &
BOT_PID=$!

echo "=== FASTAPI ==="
PYTHONPATH=backend exec uvicorn app.main:app --host 0.0.0.0 --port 8000
