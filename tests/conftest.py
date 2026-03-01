import os
import asyncio
import importlib
import uuid

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

# Force all models to register with Base.metadata before create_all runs.
# Using importlib to avoid the `import app.models.X` syntax which would
# shadow the `app` FastAPI instance imported above.
importlib.import_module("app.models.models")
importlib.import_module("app.models.ml_models")
importlib.import_module("app.models.team")
importlib.import_module("app.models.audit")

@pytest.fixture
async def engine():
    # Use a unique in-memory database name per test to avoid cross-test interference
    unique_db_name = f"memdb_{uuid.uuid4().hex}"
    url = f"sqlite+aiosqlite:///file:{unique_db_name}?mode=memory&cache=shared"
    _engine = create_async_engine(
        url,
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
    """Force all modules that imported AsyncSessionLocal to use our localized test sessionmaker."""
    import app.core.database
    import app.api.v1.endpoints.auth
    import app.api.v1.endpoints.jobs
    import app.services.scheduler

    # Override the engine and the session factory globally
    monkeypatch.setattr("app.core.database.engine", engine)
    monkeypatch.setattr("app.core.database.AsyncSessionLocal", TestingSessionLocal)
    
    # Also override in modules that might have already imported it
    # These assignments ensure existing references now point to our test factory
    monkeypatch.setattr("app.api.v1.endpoints.auth.AsyncSessionLocal", TestingSessionLocal)
    monkeypatch.setattr("app.api.v1.endpoints.jobs.AsyncSessionLocal", TestingSessionLocal)
    monkeypatch.setattr("app.services.scheduler.AsyncSessionLocal", TestingSessionLocal)

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
