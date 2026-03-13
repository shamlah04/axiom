"""
alembic/versions/0007_phase5_setup.py
──────────────────────────────────────
Phase 5: Adds 'expired' to job status and indexes for cleanup.

Revision: 0007
Down: 0006
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create the enum type if on Postgres
    connection = op.get_bind()
    if connection.engine.name == "postgresql":
        # Check if type exists
        res = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'jobstatus'"))
        if not res.first():
            op.execute("CREATE TYPE jobstatus AS ENUM ('pending', 'accepted', 'rejected', 'completed', 'expired')")
        else:
            op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'expired'")

        # 2. Alter the column to use the enum type
        # We assume it was String(30) before as per 0001_init.py
        op.execute("ALTER TABLE jobs ALTER COLUMN status TYPE jobstatus USING status::jobstatus")
    
    # 3. Create index for stale job cleanup
    op.create_index(
        "ix_jobs_pending_created",
        "jobs",
        ["status", "created_at"],
        postgresql_where="status = 'pending'",
    )

def downgrade() -> None:
    op.drop_index("ix_jobs_pending_created", table_name="jobs")
    # Downgrading enum types and column types is risky and dialect-dependent.
    # Keeping it as is for safety.
