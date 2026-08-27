#!/bin/sh
set -e

echo "Running migrations..."
PYTHONPATH=/app/backend alembic -c /app/backend/alembic.ini upgrade head

echo "Seeding database..."
PYTHONPATH=/app/backend python -m app.seed

echo "Starting Telegram bot..."
python /app/bot/bot.py &
BOT_PID=$!

echo "Starting FastAPI..."
PYTHONPATH=/app/backend exec uvicorn app.main:app --host 0.0.0.0 --port 8000
