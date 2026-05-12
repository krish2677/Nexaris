"""
Async SQLAlchemy engine and session factory.
Connects to Supabase-hosted PostgreSQL via asyncpg + PgBouncer.

Uses THREE layers of defense against PgBouncer prepared statement conflicts:
  1. statement_cache_size=0 in connect_args
  2. prepared_statement_cache_size=0 in connect_args  
  3. Event listener that forcibly clears any statement cache on checkout
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.asyncpg_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "ssl": "require",
        # Disable asyncpg prepared statement caching for PgBouncer compatibility.
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    },
)


# ── Belt-and-suspenders: forcibly clear statement cache on every checkout ──
@event.listens_for(engine.sync_engine, "checkout")
def _on_checkout(dbapi_connection, connection_record, connection_proxy):
    """Force-clear asyncpg's internal statement caches when a connection
    is checked out from the pool. This ensures PgBouncer compatibility
    even if connect_args didn't take effect."""
    try:
        raw = dbapi_connection.dbapi_connection
        # asyncpg's connection object has _stmt_cache
        if hasattr(raw, "_stmt_cache"):
            raw._stmt_cache.clear()
        if hasattr(raw, "_stmts_to_close"):
            raw._stmts_to_close.clear()
    except Exception:
        pass  # Fail silently — this is defense-in-depth


AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def verify_db_health() -> bool:
    """Verify database connectivity without mutating schema.
    Schema changes should be applied via SQL migrations only.
    """
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            logger.info(f"DB connected: {settings.DATABASE_URL.split('@')[1].split('/')[0]}")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
