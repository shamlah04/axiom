"""
alembic/versions/0002_add_ml_tables.py
────────────────────────────────────────
ML model versioning and prediction audit log tables.
Dialect-aware: PostgreSQL (production) + SQLite (CI/tests).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def _pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _uuid_col(name: str, *args, **kw):
    if _pg():
        from sqlalchemy.dialects.postgresql import UUID
        return sa.Column(name, UUID(as_uuid=True), *args, **kw)
    return sa.Column(name, sa.String(36), *args, **kw)


def _json_col(name: str, *args, **kw):
    if _pg():
        from sqlalchemy.dialects.postgresql import JSONB
        return sa.Column(name, JSONB, *args, **kw)
    return sa.Column(name, sa.Text, *args, **kw)


def _now():
    return sa.text("now()") if _pg() else sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    # ── ml_model_versions ─────────────────────────────────────────────────
    op.create_table(
        "ml_model_versions",
        _uuid_col("id", primary_key=True),
        sa.Column("version", sa.String(20), unique=True, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("training_samples", sa.Integer(), nullable=False),
        sa.Column("train_rmse", sa.Float(), nullable=False),
        sa.Column("train_r2", sa.Float(), nullable=False),
        sa.Column("test_rmse", sa.Float(), nullable=True),
        sa.Column("test_r2", sa.Float(), nullable=True),
        _json_col("feature_names", nullable=False),
        sa.Column("model_path", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False,
                  server_default=sa.text("0" if not _pg() else "false")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=_now(), nullable=False),
    )
    op.create_index("ix_ml_model_versions_is_active", "ml_model_versions", ["is_active"])

    # ── prediction_logs ───────────────────────────────────────────────────
    op.create_table(
        "prediction_logs",
        _uuid_col("id", primary_key=True),
        _uuid_col("job_id", sa.ForeignKey("jobs.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        _uuid_col("fleet_id", nullable=False),
        _uuid_col("model_version_id",
                  sa.ForeignKey("ml_model_versions.id"), nullable=True),
        sa.Column("used_ml_model", sa.Boolean(), nullable=False,
                  server_default=sa.text("0" if not _pg() else "false")),
        sa.Column("predicted_net_profit", sa.Float(), nullable=False),
        sa.Column("predicted_total_cost", sa.Float(), nullable=False),
        sa.Column("predicted_margin_pct", sa.Float(), nullable=False),
        _json_col("features_snapshot", nullable=True),
        # Actuals (filled in later)
        sa.Column("actual_revenue", sa.Float(), nullable=True),
        sa.Column("actual_cost", sa.Float(), nullable=True),
        sa.Column("actual_margin_pct", sa.Float(), nullable=True),
        sa.Column("error_amount", sa.Float(), nullable=True),
        sa.Column("error_pct", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=_now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_prediction_logs_job_id", "prediction_logs", ["job_id"])
    op.create_index("ix_prediction_logs_fleet_id", "prediction_logs", ["fleet_id"])


def downgrade() -> None:
    op.drop_index("ix_prediction_logs_fleet_id", table_name="prediction_logs")
    op.drop_index("ix_prediction_logs_job_id", table_name="prediction_logs")
    op.drop_table("prediction_logs")
    op.drop_index("ix_ml_model_versions_is_active", table_name="ml_model_versions")
    op.drop_table("ml_model_versions")
