"""
app/repositories/team_repository.py
─────────────────────────────────────
Data access for team invitations and team member management.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team import TeamInvite, UserRole, InviteStatus
from app.models.models import User

INVITE_EXPIRY_DAYS = 7


class TeamRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Invites ─────────────────────────────────────────────────────────

    async def create_invite(
        self,
        fleet_id: uuid.UUID,
        invited_by: uuid.UUID,
        email: str,
        role: UserRole,
    ) -> TeamInvite:
        # Check for existing pending invite to same email in same fleet
        existing = await self.get_pending_invite_by_email(fleet_id, email)
        if existing:
            # Revoke the old one and issue a fresh token
            await self.revoke_invite(existing.id)

        token = secrets.token_hex(32)  # 64 char hex string
        expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS)

        invite = TeamInvite(
            id=uuid.uuid4(),
            fleet_id=fleet_id,
            invited_by_user_id=invited_by,
            email=email,
            role=role,
            token=token,
            status=InviteStatus.pending,
            expires_at=expires_at,
        )
        self.db.add(invite)
        await self.db.commit()
        await self.db.refresh(invite)
        return invite

    async def get_invite_by_token(self, token: str) -> Optional[TeamInvite]:
        result = await self.db.execute(
            select(TeamInvite).where(TeamInvite.token == token)
        )
        return result.scalar_one_or_none()

    async def get_pending_invite_by_email(
        self, fleet_id: uuid.UUID, email: str
    ) -> Optional[TeamInvite]:
        result = await self.db.execute(
            select(TeamInvite).where(
                and_(
                    TeamInvite.fleet_id == fleet_id,
                    TeamInvite.email == email,
                    TeamInvite.status == InviteStatus.pending,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_invites(
        self, fleet_id: uuid.UUID, status: Optional[InviteStatus] = None
    ) -> list[TeamInvite]:
        q = select(TeamInvite).where(TeamInvite.fleet_id == fleet_id)
        if status:
            q = q.where(TeamInvite.status == status)
        q = q.order_by(TeamInvite.created_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def accept_invite(self, invite: TeamInvite, user: User) -> TeamInvite:
        """
        Accept an invite: set user's fleet_id + role, mark invite accepted.
        """
        now = datetime.now(timezone.utc)

        # Mark expired if past expiry
        exp = invite.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            invite.status = InviteStatus.expired
            await self.db.commit()
            return invite

        # Set user's fleet and role
        user.fleet_id = invite.fleet_id
        user.role = invite.role

        # Mark invite accepted
        invite.status = InviteStatus.accepted
        invite.accepted_at = now

        await self.db.commit()
        await self.db.refresh(invite)
        return invite

    async def revoke_invite(self, invite_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(TeamInvite).where(TeamInvite.id == invite_id)
        )
        invite = result.scalar_one_or_none()
        if not invite:
            return False
        invite.status = InviteStatus.revoked
        await self.db.commit()
        return True

    async def expire_stale_invites(self, fleet_id: uuid.UUID) -> int:
        """Mark all pending invites past expiry as expired. Returns count updated."""
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(TeamInvite).where(
                and_(
                    TeamInvite.fleet_id == fleet_id,
                    TeamInvite.status == InviteStatus.pending,
                    TeamInvite.expires_at < now,
                )
            )
        )
        stale = result.scalars().all()
        for inv in stale:
            inv.status = InviteStatus.expired
        if stale:
            await self.db.commit()
        return len(stale)

    # ── Team members ────────────────────────────────────────────────────

    async def list_members(self, fleet_id: uuid.UUID) -> list[User]:
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.fleet_id == fleet_id,
                    User.is_active == True,
                )
            ).order_by(User.created_at)
        )
        return list(result.scalars().all())

    async def update_member_role(
        self, fleet_id: uuid.UUID, user_id: uuid.UUID, new_role: UserRole
    ) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(
                and_(User.id == user_id, User.fleet_id == fleet_id)
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.role = new_role
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def remove_member(
        self, fleet_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """
        Remove a user from fleet: clear fleet_id and role.
        Does not delete the account — user can join another fleet later.
        """
        result = await self.db.execute(
            select(User).where(
                and_(User.id == user_id, User.fleet_id == fleet_id)
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            return False
        user.fleet_id = None
        user.role = UserRole.viewer   # reset to least-privilege
        await self.db.commit()
        return True
