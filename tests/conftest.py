"""
tests/conftest.py
──────────────────
Test fixtures for the full test suite.

DATABASE strategy:
  - CI (GitHub Actions): uses Postgres via DATABASE_URL env var set in ci.yml
    → matches production exactly, supports all DDL
  - Local dev without Postgres: falls back to in-memory SQLite
    → fast, zero-setup, but only suitable for basic smoke tests

The conftest reads DATABASE_URL from the environment and uses it directly.
No more hardcoded sqlite:// override — that was the cause of the migration crash.
"""
from __future__ import annotations

import asyncio
import importlib
import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

# ── Disable scheduler and external services in all tests ─────────────────────
os.environ.setdefault("SCHEDULER_ENABLED", "False")
os.environ.setdefault("RESEND_API_KEY", "disabled")
os.environ.setdefault("STRIPE_SECRET_KEY", "disabled")
os.environ.setdefault("TESTING", "True")
os.environ.setdefault(
    "SECRET_KEY", "ci-testing-secret-key-that-is-long-enough-32chars"
)

# ── Database URL ──────────────────────────────────────────────────────────────
# In CI, DATABASE_URL is set to postgresql+asyncpg://... by ci.yml
# Locally without Postgres, falls back to in-memory SQLite
_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true",
)
_IS_SQLITE = _DATABASE_URL.startswith("sqlite")

# Ensure settings reads the right URL before app imports
os.environ["DATABASE_URL"] = _DATABASE_URL

# ── Import app after env is set ───────────────────────────────────────────────
from app.main import app
from app.core.database import Base, get_db

# Force all models to register with Base.metadata before create_all runs
importlib.import_module("app.models.models")
importlib.import_module("app.models.ml_models")
importlib.import_module("app.models.team")
importlib.import_module("app.models.audit")


# ── Engine ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the whole session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """
    Session-scoped engine.
    - Postgres: NullPool (no connection sharing between async tests)
    - SQLite: StaticPool with shared memory DB
    """
    if _IS_SQLITE:
        _engine = create_async_engine(
            _DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        _engine = create_async_engine(
            _DATABASE_URL,
            poolclass=NullPool,
        )

    # Create all tables once for the session
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield _engine

    # Drop all tables after the session
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await _engine.dispose()


@pytest.fixture(scope="session")
def TestingSessionLocal(engine):
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# ── Per-test DB cleanup ───────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
async def clean_tables(engine):
    """
    Truncate all tables between tests to ensure isolation.
    Works on both Postgres (TRUNCATE ... RESTART IDENTITY CASCADE)
    and SQLite (DELETE FROM each table).
    """
    yield  # run the test

    async with engine.begin() as conn:
        if _IS_SQLITE:
            # SQLite: delete in reverse dependency order
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())
        else:
            # Postgres: fast truncate with cascade
            table_names = ", ".join(
                f'"{t.name}"' for t in Base.metadata.sorted_tables
            )
            from sqlalchemy import text
            await conn.execute(
                text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
            )


# ── Session and client fixtures ───────────────────────────────────────────────

@pytest.fixture
async def db_session(TestingSessionLocal):
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
def override_db_internals(monkeypatch, engine, TestingSessionLocal):
    """Redirect all AsyncSessionLocal references to the test session factory."""
    import app.core.database
    import app.api.v1.endpoints.auth
    import app.api.v1.endpoints.jobs
    import app.services.scheduler

    monkeypatch.setattr("app.core.database.engine", engine)
    monkeypatch.setattr("app.core.database.AsyncSessionLocal", TestingSessionLocal)
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
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
