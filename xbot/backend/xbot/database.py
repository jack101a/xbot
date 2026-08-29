from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.config import settings

# Create async engine for SQLite (or other database)
engine = create_async_engine(settings.DATABASE_URL, echo=False)

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
    """Initializes all database tables from Base metadata."""
    from xbot.models.base import Base
    import xbot.models  # Ensure all models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

