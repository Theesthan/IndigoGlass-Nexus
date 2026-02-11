# =============================================================================
# IndigoGlass Nexus - MySQL Database Connection
# =============================================================================
"""
Async MySQL connection using SQLAlchemy 2.x with asyncmy driver.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.core.config import settings

logger = structlog.get_logger()

# Global engine and session maker
_engine: Optional[AsyncEngine] = None
_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def init_mysql() -> None:
    """Initialize MySQL connection pool."""
    global _engine, _session_maker
    
    _engine = create_async_engine(
        settings.MYSQL_URL,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    
    _session_maker = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    logger.info("mysql_initialized", host=settings.MYSQL_HOST, database=settings.MYSQL_DATABASE)


async def close_mysql() -> None:
    """Close MySQL connection pool."""
    global _engine, _session_maker
    
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_maker = None
        logger.info("mysql_closed")


def get_engine() -> AsyncEngine:
    """Get the SQLAlchemy engine."""
    if not _engine:
        raise RuntimeError("MySQL not initialized. Call init_mysql() first.")
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get an async database session."""
    if not _session_maker:
        raise RuntimeError("MySQL not initialized. Call init_mysql() first.")
    
    async with _session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions (for non-FastAPI use)."""
    if not _session_maker:
        raise RuntimeError("MySQL not initialized. Call init_mysql() first.")
    
    async with _session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_mysql_health() -> bool:
    """Check if MySQL is healthy."""
    try:
        if not _engine:
            return False
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("mysql_health_check_failed", error=str(e))
        return False
