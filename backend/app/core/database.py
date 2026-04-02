"""
backend/app/core/database.py
-----------------------------
SQLAlchemy async database setup for PostgreSQL.

Provides:
    engine        — async SQLAlchemy engine (asyncpg driver)
    AsyncSessionLocal — async session factory
    Base          — declarative base class imported by all models/
    get_db()      — FastAPI dependency that yields a session per request
    create_tables() — called once at startup to create all tables

Why async?
----------
FastAPI is an async framework.  Using a synchronous SQLAlchemy engine
blocks the event loop during every database query — under load this
stalls all concurrent requests.  The async engine (asyncpg) releases
the event loop while waiting for Postgres, allowing FastAPI to handle
other requests in parallel.

Driver chain
------------
    SQLAlchemy async  →  asyncpg  →  PostgreSQL
    (pip install sqlalchemy asyncpg)

For Alembic migrations (sync only):
    SQLAlchemy sync   →  psycopg2  →  PostgreSQL
    (pip install psycopg2-binary)
    Uses DATABASE_URL_SYNC from config.py.

Usage in route handlers
------------------------
    from app.core.database import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    @router.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(User))
        ...

Usage in main.py lifespan
--------------------------
    from app.core.database import create_tables

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await create_tables()   # create tables on startup
        yield
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ---------------------------------------------------------------------------
# Async engine
# ---------------------------------------------------------------------------
# pool_pre_ping=True: tests connection health before using it from the pool.
# Prevents "connection already closed" errors after Postgres restarts or
# after long idle periods.
#
# pool_size=10: max persistent connections in the pool.
# max_overflow=20: allows up to 20 extra connections under burst load,
#   which are closed after use rather than returned to the pool.
#
# echo=settings.DEBUG: logs every SQL statement when DEBUG=True.
# Turn off in production — logs contain query values which may include PII.

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping  = True,
    pool_size      = 10,
    max_overflow   = 20,
    echo           = settings.DEBUG,
)


# ---------------------------------------------------------------------------
# Async session factory
# ---------------------------------------------------------------------------
# expire_on_commit=False: prevents SQLAlchemy from expiring ORM objects
# after a commit.  Without this, accessing an attribute after commit
# triggers an implicit SELECT, which fails in async context because there
# is no active transaction.

AsyncSessionLocal = async_sessionmaker(
    bind            = engine,
    class_          = AsyncSession,
    expire_on_commit= False,
    autocommit      = False,
    autoflush       = False,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
# All SQLAlchemy model classes in models/ must inherit from Base.
# Base.metadata holds all table definitions and is used by create_tables().

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    Import and inherit in every model:
        from app.core.database import Base

        class User(Base):
            __tablename__ = "users"
            ...
    """
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency — yields one session per request
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session for one request.

    Opens a session at the start of the request and closes it when the
    request completes (or raises an exception).  The session is NOT
    committed here — each service/route is responsible for committing
    its own transactions so partial writes are never silently saved.

    Usage:
        @router.post("/upload")
        async def upload(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Table creation — called once at application startup
# ---------------------------------------------------------------------------

async def create_tables() -> None:
    """
    Create all tables defined in models/ if they do not already exist.

    Uses Base.metadata.create_all() which is safe to call on an existing
    database — it only creates tables that are missing, never drops or
    alters existing ones.

    For schema migrations in production, use Alembic instead:
        alembic revision --autogenerate -m "description"
        alembic upgrade head

    Called from main.py lifespan:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await create_tables()
            yield
    """
    # Import all models here so Base.metadata knows about their tables.
    # If a model is not imported before create_all(), its table is skipped.
    import app.models.user             # noqa: F401
    import app.models.forensic_image   # noqa: F401
    import app.models.similarity_result# noqa: F401
    import app.models.report           # noqa: F401
    import app.models.dataset          # noqa: F401
    import app.models.audit_log        # noqa: F401
    import app.models.feedback         # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Database tables created (or already exist).")


# ---------------------------------------------------------------------------
# Health check helper
# ---------------------------------------------------------------------------

async def check_db_connection() -> bool:
    """
    Test that the database is reachable.
    Used by the /health endpoint in routes_admin.py.

    Returns True if connection succeeds, False otherwise.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception:
        return False