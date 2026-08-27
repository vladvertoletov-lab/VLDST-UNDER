#!/bin/sh
set -e

echo "Running migrations..."
PYTHONPATH=/app/backend alembic -c /app/backend/alembic.ini upgrade head

echo "Seeding database..."
PYTHONPATH=/app/backend python -m app.seed

echo "Starting Telegram bot..."
python /app/bot/bot.py &
BOT_PID=$!

cleanup() {
    echo "Stopping Telegram bot..."
    kill "$BOT_PID" 2>/dev/null || true
    wait "$BOT_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "Starting FastAPI..."
PYTHONPATH=/app/backend uvicorn app.main:app --host 0.0.0.0 --port 8000 &
WEB_PID=$!

wait "$WEB_PID"
