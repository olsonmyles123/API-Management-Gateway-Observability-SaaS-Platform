import asyncio
import sys
import pytest
import pytest_asyncio
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.core.database import Base, get_db
import app.core.database as db_core
import app.core.redis as redis_core
from app.core.clickhouse import clear_in_memory_telemetry
from app.main import app

# In-memory SQLite async database for test isolation
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_environment(monkeypatch):
    """Initializes tables and isolated in-memory Redis and ClickHouse for each test."""
    clear_in_memory_telemetry()
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_core, "_redis_client", fake_redis)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Override get_db dependency
    async def override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    # Default mock active admin user for authenticated control plane tests
    from app.core.security import get_current_active_user
    from app.models.user import User
    mock_admin = User(
        id="test-admin-uuid-1234",
        email="admin@enterprise.local",
        hashed_password="hashed_pw_test",
        full_name="Admin Test",
        role="admin",
        is_active=True,
    )

    async def override_get_current_active_user():
        return mock_admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    monkeypatch.setattr(db_core, "async_session_factory", test_session_factory)
    
    # Also patch wherever async_session_factory was imported directly
    if "app.api.gateway.proxy" in sys.modules:
        monkeypatch.setattr(sys.modules["app.api.gateway.proxy"], "async_session_factory", test_session_factory)
    if "app.workers.alert_worker" in sys.modules:
        monkeypatch.setattr(sys.modules["app.workers.alert_worker"], "async_session_factory", test_session_factory)

    yield

    app.dependency_overrides.clear()
    await fake_redis.aclose()


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
