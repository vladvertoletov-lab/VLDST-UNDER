#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BACKEND="$ROOT/backend"
BOT="$ROOT/bot"

echo "=== VLDST START ==="
echo "ROOT=$ROOT"
echo "BACKEND=$BACKEND"
echo "BOT=$BOT"

echo "=== CHECK FILES ==="
test -f "$BACKEND/alembic.ini"
test -d "$BACKEND/migrations"
test -f "$BACKEND/migrations/env.py"
test -f "$BACKEND/app/db.py"
test -f "$ROOT/app.py" || true

echo "=== MIGRATIONS ==="
cd "$BACKEND"
PYTHONPATH="$BACKEND" alembic -c "$BACKEND/alembic.ini" upgrade head

echo "=== SEED ==="
PYTHONPATH="$BACKEND" python -m app.seed

echo "=== BOT ==="
cd "$ROOT"
PYTHONPATH="$BACKEND:$BOT" python "$BOT/bot.py" &
BOT_PID=$!

echo "=== FASTAPI ==="
cd "$BACKEND"
PYTHONPATH="$BACKEND" exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"

kill "$BOT_PID" 2>/dev/null || true
