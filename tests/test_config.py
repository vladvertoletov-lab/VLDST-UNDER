from app.config import Settings


def test_render_postgres_url_is_normalized():
    s = Settings(database_url="postgres://u:p@host:5432/db")
    assert s.database_url_async == "postgresql+asyncpg://u:p@host:5432/db"
    assert s.database_url_sync == "postgresql://u:p@host:5432/db"


def test_async_postgres_url_is_kept():
    s = Settings(database_url="postgresql+asyncpg://u:p@host:5432/db")
    assert s.database_url_async == "postgresql+asyncpg://u:p@host:5432/db"
