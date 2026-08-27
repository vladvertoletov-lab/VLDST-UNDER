#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

echo "=== VLDST START ==="
echo "ROOT=$ROOT_DIR"
echo "BACKEND=$BACKEND_DIR"

[ -d "$BACKEND_DIR" ] || {
    echo "ERROR: backend directory not found"
    exit 1
}

[ -d "$BACKEND_DIR/migrations" ] || {
    echo "ERROR: migrations directory not found"
    exit 1
}

[ -f "$BACKEND_DIR/alembic.ini" ] || {
    echo "ERROR: alembic.ini not found"
    exit 1
}

cd "$BACKEND_DIR"

echo "=== BACKEND ==="
echo "PWD=$(pwd)"

echo "=== MIGRATION FILES ==="
find migrations -maxdepth 2 -type f -print

echo "=== MIGRATIONS ==="
PYTHONPATH="$BACKEND_DIR" alembic \
    -c "$BACKEND_DIR/alembic.ini" \
    upgrade head

echo "=== API START ==="

exec PYTHONPATH="$BACKEND_DIR" uvicorn \
    app.main:app \
    --host 0.0.0.0 \
    --port "${PORT}"
