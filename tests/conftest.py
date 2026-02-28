import os
import asyncio
import importlib

# ── Environment Overrides ───────────────────────────────────────────
os.environ["SCHEDULER_ENABLED"] = "False"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///file:memdb1?mode=memory&cache=shared"
os.environ["TESTING"] = "True"
# ────────────────────────────────────────────────────────────────────

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

# Force all models to register with Base.metadata before create_all runs.
# Using importlib to avoid the `import app.models.X` syntax which would
# shadow the `app` FastAPI instance imported above.
importlib.import_module("app.models.models")
importlib.import_module("app.models.ml_models")
importlib.import_module("app.models.team")
importlib.import_module("app.models.audit")

SQLITE_DATABASE_URL = "sqlite+aiosqlite:///file:memdb1?mode=memory&cache=shared"

@pytest.fixture
async def engine():
    _engine = create_async_engine(
        SQLITE_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield _engine
    await _engine.dispose()

@pytest.fixture
def TestingSessionLocal(engine):
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

@pytest.fixture(autouse=True)
async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(TestingSessionLocal):
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture(autouse=True)
def override_database_internals(monkeypatch, engine, TestingSessionLocal):
    """Force all background tasks and dependencies to use our test engine and sessionmaker."""
    import app.core.database
    monkeypatch.setattr("app.core.database.engine", engine)
    monkeypatch.setattr("app.core.database.AsyncSessionLocal", TestingSessionLocal)

@pytest.fixture(autouse=True)
async def override_get_db(db_session):
    async def _get_test_db():
        yield db_session
    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()

@pytest.fixture
async def client():
    # Explicitly using ASGITransport with the app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
