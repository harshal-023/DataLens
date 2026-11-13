from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import logger

# Initialize async engine with connection pooling and pre-ping validation
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG and settings.APP_ENV == "development",
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    connect_args={"timeout": 2.0},
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session per request.
    Ensures safe rollback on exception and guaranteed closure in finally.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            await session.close()


async def check_database_connection() -> tuple[bool, str | None]:
    """
    Verifies live connectivity to the PostgreSQL instance.
    Returns (True, None) on success, or (False, error_message) on failure.
    Does not expose sensitive credentials.
    """
    try:
        async with engine.connect() as conn:
            # Simple fast query to verify roundtrip connection
            await conn.execute(text("SELECT 1"))
            return True, None
    except Exception as exc:
        err_type = type(exc).__name__
        logger.warning(f"Database readiness probe failed ({err_type}): {exc}")
        return False, f"Database connectivity error: {err_type}"
