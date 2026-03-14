"""
alembic/versions/0007_add_job_status_expired.py
────────────────────────────────────────────────
Phase 5: Adds 'expired' to job status + index for stale job cleanup.

NOTE: This is revision 0007, not 0006, because 0006 already exists
(it adds stripe_customer_id to fleets). Check your chain with:
  alembic history

If your chain ends at 0006, set down_revision = "0006" below and use 0007.
If it ends at 0005, set down_revision = "0005" and rename to 0006.

Dialect-aware: PostgreSQL ALTER TYPE + SQLite no-op (SQLite stores status
as VARCHAR and already accepts any value).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"   # adjust if your chain differs
branch_labels = None
depends_on = None


def _pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if _pg():
        # PostgreSQL: extend the enum type
        op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'expired'")
        # Index to speed up the scheduler's stale-job cleanup query
        op.create_index(
            "ix_jobs_pending_created",
            "jobs",
            ["status", "created_at"],
            postgresql_where="status = 'pending'",
        )
    else:
        # SQLite: status is already VARCHAR — 'expired' is already a valid value.
        # Just add the plain index (no partial index support in SQLite).
        op.create_index(
            "ix_jobs_pending_created",
            "jobs",
            ["status", "created_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_jobs_pending_created", table_name="jobs")
    # PostgreSQL: cannot remove enum values without recreating type — skip.
