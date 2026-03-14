"""
alembic/versions/0004_add_team_and_roles.py
─────────────────────────────────────────────
Phase 3: Team management and user roles.
Dialect-aware rewrite — the original used Postgres-only DDL that crashed SQLite.

Changes:
  1. Add `role` column to `users` table (owner | dispatcher | viewer)
  2. Create `team_invites` table
  3. Backfill: existing users in a fleet get role='owner'
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _uuid_col(name: str, *args, **kw):
    if _pg():
        from sqlalchemy.dialects.postgresql import UUID
        return sa.Column(name, UUID(as_uuid=True), *args, **kw)
    return sa.Column(name, sa.String(36), *args, **kw)


def _now():
    return sa.text("now()") if _pg() else sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    pg = _pg()

    # ── 1. Add role column to users ───────────────────────────────────────
    # Store as VARCHAR on both dialects — avoids CREATE TYPE entirely.
    # The Python enum (UserRole) enforces valid values; DB stores the string.
    op.add_column(
        "users",
        sa.Column("role", sa.String(50), nullable=True),
    )

    # Backfill
    op.execute("UPDATE users SET role = 'owner'  WHERE fleet_id IS NOT NULL")
    op.execute("UPDATE users SET role = 'viewer' WHERE fleet_id IS NULL")

    # Make NOT NULL.
    # SQLite cannot do ALTER COLUMN SET NOT NULL — we use a batch migration instead.
    if pg:
        op.execute("ALTER TABLE users ALTER COLUMN role SET NOT NULL")
    else:
        with op.batch_alter_table("users") as batch:
            batch.alter_column("role", nullable=False)

    # ── 2. Create team_invites table ──────────────────────────────────────
    # All enum-like columns use VARCHAR — values validated at application layer.
    # TIMESTAMPTZ → DateTime(timezone=True) which SQLAlchemy maps correctly per dialect.
    op.create_table(
        "team_invites",
        _uuid_col("id", primary_key=True),
        _uuid_col("fleet_id",
                  sa.ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False),
        _uuid_col("invited_by_user_id",
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email",      sa.String(255), nullable=False),
        sa.Column("role",       sa.String(50),  nullable=False),
        sa.Column("token",      sa.String(64),  nullable=False, unique=True),
        sa.Column("status",     sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=_now(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_team_invites_fleet_id", "team_invites", ["fleet_id"])
    op.create_index("ix_team_invites_token",    "team_invites", ["token"])
    op.create_index("ix_team_invites_email",    "team_invites", ["email"])


def downgrade() -> None:
    op.drop_index("ix_team_invites_email",    table_name="team_invites")
    op.drop_index("ix_team_invites_token",    table_name="team_invites")
    op.drop_index("ix_team_invites_fleet_id", table_name="team_invites")
    op.drop_table("team_invites")

    if _pg():
        op.execute("ALTER TABLE users DROP COLUMN IF EXISTS role")
    else:
        with op.batch_alter_table("users") as batch:
            batch.drop_column("role")
