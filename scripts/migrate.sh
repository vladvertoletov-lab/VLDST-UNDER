#!/usr/bin/env sh
set -eu
PYTHONPATH=backend alembic -c backend/alembic.ini upgrade head
