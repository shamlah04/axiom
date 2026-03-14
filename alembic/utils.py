"""
alembic/utils.py
─────────────────
Shared utilities for dialect-aware migrations.

SQLite (used in CI/tests) does not support:
  - CREATE TYPE ... AS ENUM
  - ALTER TYPE ... ADD VALUE
  - TIMESTAMPTZ  (use DATETIME instead)
  - gen_random_uuid()  (use a Python default instead)
  - postgresql.UUID / postgresql.JSONB column types
  - ALTER TABLE ... ALTER COLUMN ... SET NOT NULL  (requires table recreation)

All migrations import is_postgres() / is_sqlite() to branch accordingly.
"""
from __future__ import annotations

from alembic import op


def dialect_name() -> str:
    return op.get_bind().dialect.name  # "postgresql" | "sqlite"


def is_postgres() -> bool:
    return dialect_name() == "postgresql"


def is_sqlite() -> bool:
    return dialect_name() == "sqlite"
