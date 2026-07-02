"""
Alembic env.py – connects our SQLAlchemy models to Alembic migration engine.
Uses asyncpg driver throughout. psycopg2 is NOT required.
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# ── Import models so Alembic can detect schema changes ─────────────────────────
from app.config import get_settings
from app.database import Base
import app.models  # noqa: F401 – registers all ORM models with Base.metadata

settings = get_settings()

# ── Alembic Config Object ──────────────────────────────────────────────────────
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# The asyncpg URL – used for all live connections
ASYNC_URL = settings.database_url  # e.g. postgresql+asyncpg://...?ssl=require


# ─────────────────────────────────────────────────────────────────────────────
#  Offline mode – generates SQL scripts without a live DB connection
#  We set the dialect explicitly so Alembic can render DDL without connecting.
# ─────────────────────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    context.configure(
        url=ASYNC_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ─────────────────────────────────────────────────────────────────────────────
#  Online mode – runs migrations against a live DB via asyncpg
# ─────────────────────────────────────────────────────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations synchronously inside it."""
    connectable = create_async_engine(
        ASYNC_URL,
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ─────────────────────────────────────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
