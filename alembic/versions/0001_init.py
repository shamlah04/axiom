"""init

Revision ID: 0001_init
Revises:
Create Date: 2026-02-21

Initial schema for FCIP Phase 1.
Tables: fleets, users, trucks, drivers, jobs
Enums: fueltype, risklevel, jobrecommendation, subscriptiontier
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enums are created implicitly by SQLAlchemy during table creation.

    # ------------------------------------------------------------------
    # fleets
    # ------------------------------------------------------------------
    op.create_table(
        "fleets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(10), server_default="DK"),
        sa.Column(
            "subscription_tier",
            sa.Enum("tier1", "tier2", "tier3", name="subscriptiontier"),
            server_default="tier1",
            nullable=False,
        ),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fleet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fleets.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------
    # trucks
    # ------------------------------------------------------------------
    op.create_table(
        "trucks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fleet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fleets.id"),
            nullable=False,
        ),
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
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_trucks_fleet_id", "trucks", ["fleet_id"])

    # ------------------------------------------------------------------
    # drivers
    # ------------------------------------------------------------------
    op.create_table(
        "drivers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fleet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fleets.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hourly_rate", sa.Float(), nullable=False),
        sa.Column("monthly_fixed_cost", sa.Float(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_drivers_fleet_id", "drivers", ["fleet_id"])

    # ------------------------------------------------------------------
    # jobs
    # ------------------------------------------------------------------
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "fleet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fleets.id"),
            nullable=False,
        ),
        sa.Column(
            "truck_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trucks.id"),
            nullable=False,
        ),
        sa.Column(
            "driver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("drivers.id"),
            nullable=False,
        ),
        # Route
        sa.Column("origin", sa.String(255), nullable=False),
        sa.Column("destination", sa.String(255), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("estimated_duration_hours", sa.Float(), nullable=False),
        # Cost inputs
        sa.Column("offered_rate", sa.Float(), nullable=False),
        sa.Column("toll_costs", sa.Float(), server_default="0"),
        sa.Column("fuel_price_per_unit", sa.Float(), nullable=False),
        sa.Column("other_costs", sa.Float(), server_default="0"),
        # Prediction outputs
        sa.Column("total_cost", sa.Float(), nullable=True),
        sa.Column("net_profit", sa.Float(), nullable=True),
        sa.Column("margin_pct", sa.Float(), nullable=True),
        sa.Column(
            "risk_level",
            sa.Enum("low", "medium", "high", name="risklevel"),
            nullable=True,
        ),
        sa.Column(
            "recommendation",
            sa.Enum("accept", "review", "reject", name="jobrecommendation"),
            nullable=True,
        ),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        # Actuals
        sa.Column("actual_revenue", sa.Float(), nullable=True),
        sa.Column("actual_cost", sa.Float(), nullable=True),
        # Status / dates
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("job_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_jobs_fleet_id", "jobs", ["fleet_id"])


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("drivers")
    op.drop_table("trucks")
    op.drop_table("users")
    op.drop_table("fleets")

    # Drop enums
    for enum_name in ("jobrecommendation", "risklevel", "subscriptiontier", "fueltype"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
