from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from app import models  # noqa: F401 - registers all models with metadata
from app.config import settings
from app.db import Base


config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url_async.replace("%", "%%"))

if config.config_file_name and config.get_section(config.config_ini_section).get("loggers"):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.database_url_sync,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_connection: context.configure(
                connection=sync_connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
        )
        await connection.run_sync(lambda _: context.run_migrations())
    await connectable.dispose()


def run_migrations_online():
    import asyncio

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
