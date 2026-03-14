"""
alembic/versions/0005_add_audit_logs.py
─────────────────────────────────────────
Phase 4: Audit log table.
Dialect-aware: replaces postgresql.UUID and postgresql.JSONB with
portable equivalents that work on SQLite.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
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
    op.create_table(
        "audit_logs",
        _uuid_col("id", primary_key=True),
        sa.Column("event_type",    sa.String(80),  nullable=False),
        _uuid_col("actor_user_id", nullable=True),
        _uuid_col("fleet_id",      nullable=True),
        sa.Column("subject_id",    sa.String(255), nullable=True),
        _json_col("metadata",      nullable=True),
        sa.Column("ip_address",    sa.String(45),  nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True),
                  server_default=_now(), nullable=False),
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
