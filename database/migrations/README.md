Alembic migrations live in `backend/migrations/versions`.
Run `alembic -c backend/alembic.ini upgrade head`.
The initial revision creates the SQLAlchemy metadata; `python -m app.seed` then inserts content.
