import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

logger = logging.getLogger("gateway.database")

# Base SQLAlchemy declarative model
Base = declarative_base()

# SQLAlchemy Async Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Async Session Factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency for obtaining async database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initializes metadata tables in PostgreSQL / SQLite."""
    # Import all models to ensure they are registered on Base.metadata
    from app.models.tenant import Tenant
    from app.models.api_key import ApiKey
    from app.models.alert import AlertRule, AlertHistory
    from app.models.user import User

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database metadata schema initialized successfully")
