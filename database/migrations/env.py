"""
database/migrations/env.py
----------------------------
Alembic migration environment configuration.

This file is executed by Alembic when running migration commands:
    alembic revision --autogenerate -m "description"  # generate migration
    alembic upgrade head                              # apply all migrations
    alembic downgrade -1                              # roll back one step
    alembic history                                   # show migration history

HOW TO RUN MIGRATIONS
----------------------
From the backend/ directory:

    # First time setup — create the initial migration
    cd backend
    alembic revision --autogenerate -m "initial schema"
    alembic upgrade head

    # After adding or changing a model
    alembic revision --autogenerate -m "add evidence_type to images"
    alembic upgrade head

    # Roll back the last migration
    alembic downgrade -1

WHY ALEMBIC INSTEAD OF create_all()
--------------------------------------
create_tables() in database.py uses Base.metadata.create_all() which:
    - Only ADDS new tables, never modifies or drops columns
    - Cannot detect column type changes, renamed columns, or index changes
    - Unsafe for production — schema changes can silently do nothing

Alembic autogenerate:
    - Diffs your ORM models against the actual DB schema
    - Generates a migration script with exact ALTER TABLE statements
    - Supports upgrade AND downgrade (rollback)
    - Tracks which migrations have been applied in the alembic_version table
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------------------------
# Add backend/ to sys.path so app imports work
# ---------------------------------------------------------------------------
# Alembic runs from the database/migrations/ directory by default.
# We need to add the backend/ directory to sys.path so that
# "from app.db.base import Base" resolves correctly.

backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# ---------------------------------------------------------------------------
# Import Base with all models registered
# ---------------------------------------------------------------------------
# app/db/base.py imports Base AND all model files.
# This is required — if models are not imported, their tables are invisible
# to Alembic and autogenerate will miss them entirely.

from app.db.base import Base  # noqa: E402
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Load the database URL from the .env file
# ---------------------------------------------------------------------------
# We use the SYNC URL (psycopg2) here because Alembic runs synchronously.
# The async URL (asyncpg) is used by the FastAPI app at runtime.

from app.core.config import settings  # noqa: E402
DB_URL = settings.DATABASE_URL_SYNC

# ---------------------------------------------------------------------------
# Alembic config
# ---------------------------------------------------------------------------
config = context.config
config.set_main_option("sqlalchemy.url", DB_URL)

# Set up logging from alembic.ini if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ---------------------------------------------------------------------------
# Run migrations offline (no live DB connection — generates SQL only)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates SQL scripts without connecting to the database.
    Useful for reviewing what will change before applying.
    """
    context.configure(
        url                     = DB_URL,
        target_metadata         = target_metadata,
        literal_binds           = True,
        dialect_opts            = {"paramstyle": "named"},
        compare_type            = True,   # detect column type changes
        compare_server_default  = True,   # detect default value changes
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Run migrations online (connects to the live database)
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode — connects to PostgreSQL and applies changes.
    This is the normal mode used in development and deployment.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix      = "sqlalchemy.",
        poolclass   = pool.NullPool,   # no connection pooling for migrations
    )
    with connectable.connect() as connection:
        context.configure(
            connection              = connection,
            target_metadata         = target_metadata,
            compare_type            = True,
            compare_server_default  = True,
        )
        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()