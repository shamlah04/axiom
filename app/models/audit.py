"""
app/models/audit.py
────────────────────
Phase 4: Immutable audit log for compliance and debugging.

Captures billing, team, auth, and high-value job events.
Design: append-only, no FK constraints (rows survive user/fleet deletion).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class AuditEventType(str, enum.Enum):
    # Billing
    TIER_UPGRADED                 = "tier.upgraded"
    TRIAL_STARTED                 = "trial.started"
    TRIAL_EXPIRED                 = "trial.expired"
    STRIPE_CHECKOUT_CREATED       = "stripe.checkout_created"
    STRIPE_PAYMENT_SUCCESS        = "stripe.payment_success"
    STRIPE_PAYMENT_FAILED         = "stripe.payment_failed"
    STRIPE_SUBSCRIPTION_CANCELLED = "stripe.subscription_cancelled"

    # Team
    MEMBER_INVITED                = "team.member_invited"
    MEMBER_JOINED                 = "team.member_joined"
    MEMBER_REMOVED                = "team.member_removed"
    MEMBER_ROLE_CHANGED           = "team.role_changed"
    INVITE_REVOKED                = "team.invite_revoked"

    # Auth
    USER_REGISTERED               = "auth.registered"
    USER_LOGIN                    = "auth.login"
    USER_LOGIN_FAILED             = "auth.login_failed"

    # Jobs
    JOB_ACCEPTED                  = "job.accepted"
    JOB_REJECTED                  = "job.rejected"
    JOB_ACTUALS_RECORDED          = "job.actuals_recorded"

    # Email
    EMAIL_SENT                    = "email.sent"
    EMAIL_FAILED                  = "email.failed"


class AuditLog(Base):
    """
    Immutable audit trail. Never UPDATE or DELETE rows here.
    Use INSERT only.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)

    # No FK constraints — rows must survive user/fleet deletion
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    fleet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    subject_id: Mapped[str] = mapped_column(String(255), nullable=True)

    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_audit_logs_fleet_id",   "fleet_id"),
        Index("ix_audit_logs_actor",      "actor_user_id"),
        Index("ix_audit_logs_event_type", "event_type"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
