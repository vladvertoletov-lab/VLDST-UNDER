#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

echo "=== VLDST START ==="
echo "ROOT=$ROOT_DIR"
echo "BACKEND=$BACKEND_DIR"

if [ ! -d "$BACKEND_DIR" ]; then
    echo "ERROR: backend directory not found: $BACKEND_DIR"
    exit 1
fi

if [ ! -d "$BACKEND_DIR/migrations" ]; then
    echo "ERROR: migrations directory not found"
    exit 1
fi

if [ ! -f "$BACKEND_DIR/alembic.ini" ]; then
    echo "ERROR: alembic.ini not found"
    exit 1
fi

if [ ! -d "$ROOT_DIR/frontend" ]; then
    echo "ERROR: frontend directory not found"
    exit 1
fi

if [ ! -d "$ROOT_DIR/frontend/assets" ]; then
    echo "ERROR: frontend/assets directory not found"
    exit 1
fi

echo "=== PROJECT ==="
echo "FRONTEND=$ROOT_DIR/frontend"
echo "ASSETS=$ROOT_DIR/frontend/assets"

if [ -d "$ROOT_DIR/admin" ]; then
    echo "ADMIN=$ROOT_DIR/admin"
else
    echo "WARNING: admin directory does not exist"
fi

echo "=== BACKEND ==="
cd "$BACKEND_DIR"
echo "PWD=$(pwd)"

echo "=== MIGRATION FILES ==="
find migrations -maxdepth 2 -type f -print | sort

echo "=== ALEMBIC CURRENT ==="
PYTHONPATH="$BACKEND_DIR" alembic \
    -c "$BACKEND_DIR/alembic.ini" \
    current || true

echo "=== ALEMBIC HISTORY ==="
PYTHONPATH="$BACKEND_DIR" alembic \
    -c "$BACKEND_DIR/alembic.ini" \
    history

echo "=== ALEMBIC UPGRADE HEAD ==="
PYTHONPATH="$BACKEND_DIR" alembic \
    -c "$BACKEND_DIR/alembic.ini" \
    upgrade head

echo "=== ALEMBIC AFTER UPGRADE ==="
PYTHONPATH="$BACKEND_DIR" alembic \
    -c "$BACKEND_DIR/alembic.ini" \
    current

echo "=== MIGRATIONS DONE ==="

echo "=== API START ==="

cd "$ROOT_DIR"

echo "PWD=$(pwd)"
echo "PORT=${PORT}"

exec env PYTHONPATH="$BACKEND_DIR" uvicorn \
    app.main:app \
    --host 0.0.0.0 \
    --port "${PORT}"
