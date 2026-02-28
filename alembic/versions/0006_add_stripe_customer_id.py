"""
alembic/versions/0006_add_stripe_customer_id.py
─────────────────────────────────────────────
Phase 5: Add stripe_customer_id to fleets table.

Revision chain: 0005 → 0006
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fleets",
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_fleets_stripe_customer_id", "fleets", ["stripe_customer_id"])


def downgrade() -> None:
    op.drop_index("ix_fleets_stripe_customer_id", table_name="fleets")
    op.drop_column("fleets", "stripe_customer_id")
