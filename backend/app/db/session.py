"""
backend/app/db/session.py
--------------------------
Re-exports database session utilities for convenience.

Services and routes can import from either:
    from app.core.database import get_db, AsyncSessionLocal
    from app.db.session    import get_db, AsyncSessionLocal  ← same thing

This indirection means if the session implementation ever moves,
only this file needs updating — not every import site.
"""

from app.core.database import (   # noqa: F401
    AsyncSessionLocal,
    get_db,
    engine,
)