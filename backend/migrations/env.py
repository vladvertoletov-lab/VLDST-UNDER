from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.db import Base
from app import models
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url_async.replace("%", "%%"))
if config.config_file_name and config.get_section(config.config_ini_section).get("loggers"):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    url = settings.database_url_async.replace("+asyncpg", "")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle":"named"}, compare_type=True)
    with context.begin_transaction(): context.run_migrations()

def run_migrations_online():
    from sqlalchemy.ext.asyncio import create_async_engine
    engine=create_async_engine(settings.database_url_async, poolclass=pool.NullPool)
    async def go():
        async with engine.connect() as connection:
            await connection.run_sync(lambda c: context.configure(connection=c,target_metadata=target_metadata,compare_type=True))
            await connection.run_sync(lambda c: context.run_migrations())
        await engine.dispose()
    import asyncio; asyncio.run(go())

if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
