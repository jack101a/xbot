from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.config import settings

from sqlalchemy.pool import NullPool

# Create async engine for SQLite (or other database) with NullPool to prevent event loop connection leaks
engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Initializes all database tables from Base metadata and executes lightweight migrations."""
    from xbot.models.base import Base
    import xbot.models  # Ensure all models are registered
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("ALTER TABLE instant_trend_campaigns ADD COLUMN sentiment_tone VARCHAR(50) DEFAULT 'balanced'"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE instant_trend_campaigns ADD COLUMN ragebait_percentage INTEGER DEFAULT 0"))
        except Exception:
            pass

