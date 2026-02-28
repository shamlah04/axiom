"""
app/models/team.py
──────────────────
Phase 3 team membership models.

Adds:
  - UserRole enum: owner | dispatcher | viewer
  - TeamInvite: pending email invitations with secure token
  - User.role column (via migration 0004)

Design decisions:
  - Roles are fleet-scoped (a user has one role per fleet)
  - Role stored on User directly (not a join table) — one user, one fleet
  - Invites use a cryptographically random token (32 bytes hex)
  - Invite status: pending → accepted | revoked | expired
  - Invite expiry: 7 days
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, enum.Enum):
    owner      = "owner"       # full access: manage team, billing, all data
    dispatcher = "dispatcher"  # create/manage jobs, trucks, drivers — no billing/team
    viewer     = "viewer"      # read-only access to all fleet data


class InviteStatus(str, enum.Enum):
    pending  = "pending"
    accepted = "accepted"
    revoked  = "revoked"
    expired  = "expired"


class TeamInvite(Base):
    """
    Pending invitation for a new team member.

    Flow:
      1. Fleet owner POSTs to /team/invites with email + role
      2. Row created here with status=pending, token=random
      3. Email sent with link: /accept-invite?token={token}
      4. Invitee registers (or logs in) and POSTs to /team/invites/accept
      5. status → accepted, user.fleet_id set, user.role set
    """
    __tablename__ = "team_invites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fleet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fleets.id", ondelete="CASCADE"), nullable=False
    )
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), default="dispatcher", nullable=False
    )
    token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )  # 32-byte hex = 64 chars
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_team_invites_fleet_id", "fleet_id"),
        Index("ix_team_invites_token", "token"),
        Index("ix_team_invites_email", "email"),
    )
