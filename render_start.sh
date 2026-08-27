#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

echo "=== VLDST START ==="
echo "ROOT=$ROOT_DIR"
echo "BACKEND=$BACKEND_DIR"

echo "=== PROJECT ==="
echo "FRONTEND=$ROOT_DIR/frontend"
echo "ASSETS=$ROOT_DIR/frontend/assets"
echo "ADMIN=$ROOT_DIR/admin"

echo "=== BACKEND ==="
cd "$BACKEND_DIR"
echo "PWD=$(pwd)"

echo "=== MIGRATIONS ==="
PYTHONPATH="$BACKEND_DIR" alembic -c "$BACKEND_DIR/alembic.ini" upgrade head

echo "=== MIGRATIONS DONE ==="

echo "=== START BOT ==="
cd "$ROOT_DIR"
PYTHONPATH="$BACKEND_DIR:$ROOT_DIR/bot" python -m bot.bot &
BOT_PID=$!
echo "BOT PID=$BOT_PID"

echo "=== API START ==="
cd "$BACKEND_DIR"
exec PYTHONPATH="$BACKEND_DIR" uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT}"
