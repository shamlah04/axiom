"""
alembic/versions/0003_add_intelligence_indexes.py
──────────────────────────────────────────────────
Phase 2 DB optimisation migration.

No new tables are created — Phase 2 reads entirely from existing tables:
  jobs, fleets, trucks, prediction_logs

This migration adds composite indexes that make the intelligence queries
fast at scale (10k+ jobs per fleet).

Indexes added:
  ix_jobs_fleet_status           — benchmark + anomaly queries (fleet_id, status)
  ix_jobs_fleet_created          — trend queries (fleet_id, created_at)
  ix_jobs_fleet_margin           — percentile queries (fleet_id, margin_pct)

Run: alembic upgrade head
"""

from __future__ import annotations
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite index: fleet + status filter (benchmark, anomaly detection)
    op.create_index(
        "ix_jobs_fleet_status",
        "jobs",
        ["fleet_id", "status"],
    )

    # Composite index: fleet + time (weekly trend queries)
    op.create_index(
        "ix_jobs_fleet_created",
        "jobs",
        ["fleet_id", "created_at"],
    )

    # Composite index: fleet + margin (percentile aggregation)
    op.create_index(
        "ix_jobs_fleet_margin",
        "jobs",
        ["fleet_id", "margin_pct"],
        postgresql_where="margin_pct IS NOT NULL",  # partial index — skip nulls
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_fleet_margin", table_name="jobs")
    op.drop_index("ix_jobs_fleet_created", table_name="jobs")
    op.drop_index("ix_jobs_fleet_status", table_name="jobs")
