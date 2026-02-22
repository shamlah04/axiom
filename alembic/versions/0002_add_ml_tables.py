"""Add ML model versioning and prediction audit log tables.

Revision ID: 0002
Revises: 0001_init
Create Date: 2026-02-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ml_model_versions ────────────────────────────────────────────────
    op.create_table(
        "ml_model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.String(20), unique=True, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("training_samples", sa.Integer, nullable=False),
        sa.Column("train_rmse", sa.Float, nullable=False),
        sa.Column("train_r2", sa.Float, nullable=False),
        sa.Column("test_rmse", sa.Float, nullable=True),
        sa.Column("test_r2", sa.Float, nullable=True),
        sa.Column("feature_names", postgresql.JSONB, nullable=False),
        sa.Column("model_path", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean, default=False, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ml_model_versions_is_active", "ml_model_versions", ["is_active"])

    # ── prediction_logs ──────────────────────────────────────────────────
    op.create_table(
        "prediction_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("fleet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ml_model_versions.id"),
            nullable=True,
        ),
        sa.Column("used_ml_model", sa.Boolean, default=False, nullable=False),
        # Prediction
        sa.Column("predicted_net_profit", sa.Float, nullable=False),
        sa.Column("predicted_total_cost", sa.Float, nullable=False),
        sa.Column("predicted_margin_pct", sa.Float, nullable=False),
        sa.Column("features_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("feature_importances", postgresql.JSONB, nullable=True),
        # Actuals (filled later)
        sa.Column("actual_net_profit", sa.Float, nullable=True),
        sa.Column("actual_total_cost", sa.Float, nullable=True),
        sa.Column("actual_margin_pct", sa.Float, nullable=True),
        # Error metrics
        sa.Column("profit_error", sa.Float, nullable=True),
        sa.Column("profit_error_pct", sa.Float, nullable=True),
        sa.Column("abs_profit_error", sa.Float, nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_prediction_logs_job_id", "prediction_logs", ["job_id"])
    op.create_index("ix_prediction_logs_fleet_id", "prediction_logs", ["fleet_id"])
    op.create_index("ix_prediction_logs_model_version_id", "prediction_logs", ["model_version_id"])


def downgrade() -> None:
    op.drop_table("prediction_logs")
    op.drop_table("ml_model_versions")
