"""
alembic/versions/0005_add_audit_logs.py
─────────────────────────────────────────
Phase 4: Audit log table.

No new enums — event_type stored as plain VARCHAR(80) for extensibility.
Append-only table: no UPDATE/DELETE operations ever.

Revision chain: 0004 → 0005
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        # No FK on these — rows must survive user/fleet deletion
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fleet_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject_id", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index("ix_audit_logs_fleet_id",   "audit_logs", ["fleet_id"])
    op.create_index("ix_audit_logs_actor",       "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_event_type",  "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_created_at",  "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_event_type",  table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor",       table_name="audit_logs")
    op.drop_index("ix_audit_logs_fleet_id",    table_name="audit_logs")
    op.drop_table("audit_logs")
