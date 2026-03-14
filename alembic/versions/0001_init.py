"""
alembic/versions/0001_init.py
──────────────────────────────
Initial schema — Phase 1.
Tables: fleets, users, trucks, drivers, jobs
Dialect-aware: works on both PostgreSQL (production) and SQLite (CI/tests).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


# ── Dialect helper ────────────────────────────────────────────────────────────

def _pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _uuid_col(name: str, *args, **kw):
    """UUID column — native on Postgres, VARCHAR(36) on SQLite."""
    if _pg():
        from sqlalchemy.dialects.postgresql import UUID
        return sa.Column(name, UUID(as_uuid=True), *args, **kw)
    return sa.Column(name, sa.String(36), *args, **kw)


def _json_col(name: str, **kw):
    """JSONB on Postgres, TEXT on SQLite."""
    if _pg():
        from sqlalchemy.dialects.postgresql import JSONB
        return sa.Column(name, JSONB, **kw)
    return sa.Column(name, sa.Text, **kw)


def _now():
    """now() on Postgres, CURRENT_TIMESTAMP on SQLite."""
    return sa.text("now()") if _pg() else sa.text("CURRENT_TIMESTAMP")


# ── Migration ─────────────────────────────────────────────────────────────────

def upgrade() -> None:
    pg = _pg()

    # ── fleets ────────────────────────────────────────────────────────────
    op.create_table(
        "fleets",
        _uuid_col("id", primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(10), server_default="DK"),
        sa.Column(
            "subscription_tier",
            sa.Enum("tier1", "tier2", "tier3", name="subscriptiontier"),
            server_default="tier1",
            nullable=False,
        ),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=_now(), nullable=False),
    )

    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        _uuid_col("id", primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1" if not pg else "true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=_now(), nullable=False),
        _uuid_col("fleet_id", sa.ForeignKey("fleets.id"), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── trucks ────────────────────────────────────────────────────────────
    op.create_table(
        "trucks",
        _uuid_col("id", primary_key=True),
        _uuid_col("fleet_id", sa.ForeignKey("fleets.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("license_plate", sa.String(30), nullable=True),
        sa.Column(
            "fuel_type",
            sa.Enum("diesel", "petrol", "electric", "hybrid", name="fueltype"),
            server_default="diesel",
            nullable=False,
        ),
        sa.Column("fuel_consumption_per_100km", sa.Float(), nullable=False),
        sa.Column("maintenance_cost_per_km", sa.Float(), nullable=False),
        sa.Column("insurance_monthly", sa.Float(), nullable=False),
        sa.Column("leasing_monthly", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1" if not pg else "true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=_now(), nullable=False),
    )
    op.create_index("ix_trucks_fleet_id", "trucks", ["fleet_id"])

    # ── drivers ───────────────────────────────────────────────────────────
    op.create_table(
        "drivers",
        _uuid_col("id", primary_key=True),
        _uuid_col("fleet_id", sa.ForeignKey("fleets.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hourly_rate", sa.Float(), nullable=False),
        sa.Column("monthly_fixed_cost", sa.Float(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1" if not pg else "true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=_now(), nullable=False),
    )
    op.create_index("ix_drivers_fleet_id", "drivers", ["fleet_id"])

    # ── jobs ──────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        _uuid_col("id", primary_key=True),
        _uuid_col("fleet_id", sa.ForeignKey("fleets.id"), nullable=False),
        _uuid_col("truck_id", sa.ForeignKey("trucks.id"), nullable=False),
        _uuid_col("driver_id", sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("origin", sa.String(255), nullable=False),
        sa.Column("destination", sa.String(255), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("estimated_duration_hours", sa.Float(), nullable=False),
        sa.Column("offered_rate", sa.Float(), nullable=False),
        sa.Column("fuel_price_per_unit", sa.Float(), nullable=False),
        sa.Column("job_date", sa.DateTime(timezone=True), nullable=True),
        # Prediction outputs
        sa.Column("net_profit", sa.Float(), nullable=True),
        sa.Column("margin_pct", sa.Float(), nullable=True),
        sa.Column("total_cost", sa.Float(), nullable=True),
        sa.Column("fuel_cost", sa.Float(), nullable=True),
        sa.Column("driver_cost", sa.Float(), nullable=True),
        sa.Column("toll_cost", sa.Float(), nullable=True),
        sa.Column("maintenance_cost", sa.Float(), nullable=True),
        sa.Column("fixed_cost_allocation", sa.Float(), nullable=True),
        sa.Column("recommendation", sa.String(20), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        # Actuals
        sa.Column("actual_revenue", sa.Float(), nullable=True),
        sa.Column("actual_cost", sa.Float(), nullable=True),
        sa.Column("actual_margin_pct", sa.Float(), nullable=True),
        # Status
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=_now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_fleet_id", "jobs", ["fleet_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("drivers")
    op.drop_table("trucks")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("fleets")
