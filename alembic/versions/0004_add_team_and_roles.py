"""
alembic/versions/0004_add_team_and_roles.py
─────────────────────────────────────────────
Phase 3: Team management and user roles.

Changes:
  1. Add `role` column to `users` table (owner | dispatcher | viewer)
  2. Create `team_invites` table
  3. Backfill: existing users in a fleet get role='owner'

Revision chain: 0003 → 0004
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL for all DDL to avoid asyncpg/SQLAlchemy enum lifecycle issues

    # ── 1. Create enums ───────────────────────────────────────────────────
    op.execute("CREATE TYPE userrole AS ENUM ('owner', 'dispatcher', 'viewer')")
    op.execute("CREATE TYPE invitestatus AS ENUM ('pending', 'accepted', 'revoked', 'expired')")

    # ── 2. Add role column to users ───────────────────────────────────────
    op.execute("ALTER TABLE users ADD COLUMN role userrole")

    # Backfill: users with a fleet_id become 'owner' (they created their fleet)
    op.execute("UPDATE users SET role = 'owner' WHERE fleet_id IS NOT NULL")
    op.execute("UPDATE users SET role = 'viewer' WHERE fleet_id IS NULL")

    # Now make it NOT NULL
    op.execute("ALTER TABLE users ALTER COLUMN role SET NOT NULL")

    # ── 3. Create team_invites table ──────────────────────────────────────
    op.execute("""
        CREATE TABLE team_invites (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            fleet_id        UUID NOT NULL REFERENCES fleets(id) ON DELETE CASCADE,
            invited_by_user_id UUID NOT NULL REFERENCES users(id),
            email           VARCHAR(255) NOT NULL,
            role            userrole NOT NULL,
            token           VARCHAR(64) UNIQUE NOT NULL,
            status          invitestatus NOT NULL DEFAULT 'pending',
            expires_at      TIMESTAMPTZ NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            accepted_at     TIMESTAMPTZ
        )
    """)

    op.execute("CREATE INDEX ix_team_invites_fleet_id ON team_invites (fleet_id)")
    op.execute("CREATE INDEX ix_team_invites_token    ON team_invites (token)")
    op.execute("CREATE INDEX ix_team_invites_email    ON team_invites (email)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_team_invites_email")
    op.execute("DROP INDEX IF EXISTS ix_team_invites_token")
    op.execute("DROP INDEX IF EXISTS ix_team_invites_fleet_id")
    op.execute("DROP TABLE IF EXISTS team_invites")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS role")
    op.execute("DROP TYPE IF EXISTS invitestatus")
    op.execute("DROP TYPE IF EXISTS userrole")
