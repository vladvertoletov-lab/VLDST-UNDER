#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

export PYTHONPATH="$BACKEND_DIR:$ROOT_DIR"

cd "$ROOT_DIR"
echo "=== VLDST START ==="
echo "ROOT=$ROOT_DIR"
echo "BACKEND=$BACKEND_DIR"

[ -d "$BACKEND_DIR" ] || { echo "ERROR: backend directory not found"; exit 1; }
[ -f "$BACKEND_DIR/alembic.ini" ] || { echo "ERROR: alembic.ini not found"; exit 1; }
[ -f "$ROOT_DIR/frontend/index.html" ] || { echo "ERROR: frontend/index.html not found"; exit 1; }
[ -f "$ROOT_DIR/admin/index.html" ] || { echo "ERROR: admin/index.html not found"; exit 1; }

if [ -z "${BOT_TOKEN:-}" ]; then
    echo "ERROR: BOT_TOKEN is not set"
    exit 1
fi
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL is not set"
    exit 1
fi

if [ -z "${PORT:-}" ]; then
    PORT=10000
fi

echo "=== PROJECT ==="
echo "FRONTEND=$ROOT_DIR/frontend"
echo "ASSETS=$ROOT_DIR/frontend/assets"
echo "ADMIN=$ROOT_DIR/admin"
echo "PORT=$PORT"

echo "=== MIGRATIONS ==="
python -m alembic -c "$BACKEND_DIR/alembic.ini" upgrade head

echo "=== SEED ==="
python -m app.seed

echo "=== START BOT ==="
python -m bot.bot &
BOT_PID=$!
echo "BOT PID=$BOT_PID"

echo "=== START API ==="
uvicorn app.main:app --host 0.0.0.0 --port "$PORT" &
API_PID=$!
echo "API PID=$API_PID"

cleanup() {
    kill "$BOT_PID" "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

while :; do
    if ! kill -0 "$BOT_PID" 2>/dev/null; then
        echo "ERROR: Telegram bot process stopped"
        wait "$BOT_PID" || true
        exit 1
    fi
    if ! kill -0 "$API_PID" 2>/dev/null; then
        echo "ERROR: API process stopped"
        wait "$API_PID" || true
        exit 1
    fi
    BOT_STATE=$(ps -o stat= -p "$BOT_PID" 2>/dev/null || true)
    API_STATE=$(ps -o stat= -p "$API_PID" 2>/dev/null || true)
    case "$BOT_STATE" in Z*) echo "ERROR: Telegram bot process became zombie"; exit 1;; esac
    case "$API_STATE" in Z*) echo "ERROR: API process became zombie"; exit 1;; esac
    sleep 2
done
