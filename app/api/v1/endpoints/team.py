"""
app/api/v1/endpoints/team.py  [Phase 4 update]
───────────────────────────────────────────────
Changes vs Phase 3:
  - POST /team/invites → sends invite email (non-blocking) + writes audit log
  - POST /team/invites/accept → writes audit log
  - DELETE /team/invites/{id} → writes audit log
  - PATCH /team/members/{id}/role → writes audit log
  - DELETE /team/members/{id} → writes audit log
  - POST /fleets/me/upgrade → sends confirmation email + writes audit log
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_fleet_user, get_current_user
from app.core.roles import require_owner
from app.core.tier_limits import (
    enforce_team_invite_tier,
    build_plan_summary,
    get_limits,
)
from app.models.models import User, SubscriptionTier
from app.models.team import UserRole, InviteStatus
from app.models.audit import AuditEventType
from app.repositories.team_repository import TeamRepository
from app.repositories.repositories import FleetRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.team import (
    InviteCreate, InviteAccept, InviteOut,
    MemberOut, MemberRoleUpdate,
    PlanSummary, PlanLimits, PlanUsage, PlanFeatures,
    SubscriptionUpgrade,
)
from app.services.email_service import EmailService

team_router = APIRouter(prefix="/team", tags=["Team"])
fleet_router = APIRouter(prefix="/fleets", tags=["Fleets"])


async def _run_audit(coro):
    """If in test mode, wait for the background task to finish to avoid race conditions."""
    if settings.TESTING:
        await coro
    else:
        asyncio.create_task(coro)

_email = EmailService()


# ─────────────────────────────────────────────────────────────────────────
# Team Members
# ─────────────────────────────────────────────────────────────────────────

@team_router.get("/members", response_model=list[MemberOut])
async def list_members(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = TeamRepository(db)
    members = await repo.list_members(current_user.fleet_id)
    return [
        MemberOut(id=m.id, email=m.email, full_name=m.full_name,
                  role=m.role, is_active=m.is_active, created_at=m.created_at)
        for m in members
    ]


@team_router.patch(
    "/members/{user_id}/role",
    response_model=MemberOut,
    dependencies=[Depends(require_owner)],
)
async def update_member_role(
    user_id: uuid.UUID,
    payload: MemberRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role.")

    repo = TeamRepository(db)
    user = await repo.update_member_role(current_user.fleet_id, user_id, payload.role)
    if not user:
        raise HTTPException(status_code=404, detail="Member not found in this fleet")

    # Audit log
    audit = AuditRepository(db)
    await audit.log(
        AuditEventType.MEMBER_ROLE_CHANGED,
        actor_user_id=current_user.id,
        fleet_id=current_user.fleet_id,
        subject_id=str(user_id),
        metadata={"new_role": payload.role.value},
    )

    return MemberOut(id=user.id, email=user.email, full_name=user.full_name,
                     role=user.role, is_active=user.is_active, created_at=user.created_at)


@team_router.delete(
    "/members/{user_id}",
    status_code=204,
    dependencies=[Depends(require_owner)],
)
async def remove_member(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from the fleet.")

    repo = TeamRepository(db)
    removed = await repo.remove_member(current_user.fleet_id, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found in this fleet")

    audit = AuditRepository(db)
    await audit.log(
        AuditEventType.MEMBER_REMOVED,
        actor_user_id=current_user.id,
        fleet_id=current_user.fleet_id,
        subject_id=str(user_id),
    )


# ─────────────────────────────────────────────────────────────────────────
# Invites
# ─────────────────────────────────────────────────────────────────────────

@team_router.post(
    "/invites",
    response_model=InviteOut,
    status_code=201,
    dependencies=[Depends(require_owner), Depends(enforce_team_invite_tier)],
)
async def create_invite(
    payload: InviteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    if payload.role == UserRole.owner:
        raise HTTPException(status_code=400, detail="Cannot invite with 'owner' role.")

    fleet_repo = FleetRepository(db)
    fleet = await fleet_repo.get(current_user.fleet_id)
    limits = get_limits(fleet.subscription_tier)

    team_repo = TeamRepository(db)
    members = await team_repo.list_members(current_user.fleet_id)
    pending = await team_repo.list_invites(current_user.fleet_id, status=InviteStatus.pending)

    if len(members) + len(pending) >= limits["max_team_members"]:
        raise HTTPException(
            status_code=403,
            detail=f"Team member limit reached for {limits['label']}. Upgrade your plan."
        )

    existing = next((m for m in members if m.email == payload.email), None)
    if existing:
        raise HTTPException(status_code=409, detail=f"{payload.email} is already a member.")

    invite = await team_repo.create_invite(
        fleet_id=current_user.fleet_id,
        invited_by=current_user.id,
        email=payload.email,
        role=payload.role,
    )

    # Audit log
    audit = AuditRepository(db)
    await audit.log(
        AuditEventType.MEMBER_INVITED,
        actor_user_id=current_user.id,
        fleet_id=current_user.fleet_id,
        subject_id=payload.email,
        metadata={"role": payload.role.value, "invite_id": str(invite.id)},
    )

    # Send invite email
    await _run_audit(
        _email.send_team_invite(
            to_email=payload.email,
            fleet_name=fleet.name,
            inviter_name=current_user.full_name,
            role=payload.role.value,
            invite_token=invite.token,
        )
    )

    return invite


@team_router.get("/invites", response_model=list[InviteOut], dependencies=[Depends(require_owner)])
async def list_invites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = TeamRepository(db)
    await repo.expire_stale_invites(current_user.fleet_id)
    return await repo.list_invites(current_user.fleet_id)


@team_router.delete(
    "/invites/{invite_id}",
    status_code=204,
    dependencies=[Depends(require_owner)],
)
async def revoke_invite(
    invite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = TeamRepository(db)
    invites = await repo.list_invites(current_user.fleet_id)
    if not any(i.id == invite_id for i in invites):
        raise HTTPException(status_code=404, detail="Invite not found")
    await repo.revoke_invite(invite_id)

    audit = AuditRepository(db)
    await audit.log(
        AuditEventType.INVITE_REVOKED,
        actor_user_id=current_user.id,
        fleet_id=current_user.fleet_id,
        subject_id=str(invite_id),
    )


@team_router.post("/invites/accept", response_model=MemberOut)
async def accept_invite(
    payload: InviteAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.fleet_id:
        raise HTTPException(status_code=409, detail="You are already a member of a fleet.")

    repo = TeamRepository(db)
    invite = await repo.get_invite_by_token(payload.token)

    if not invite:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation token.")
    if invite.status == InviteStatus.revoked:
        raise HTTPException(status_code=400, detail="This invitation has been revoked.")
    if invite.status == InviteStatus.accepted:
        raise HTTPException(status_code=400, detail="This invitation has already been used.")
    if invite.status == InviteStatus.expired:
        raise HTTPException(status_code=400, detail="This invitation has expired.")

    now = datetime.now(timezone.utc)
    exp = invite.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        invite.status = InviteStatus.expired
        await db.commit()
        raise HTTPException(status_code=400, detail="This invitation has expired.")

    if current_user.email.lower() != invite.email.lower():
        raise HTTPException(
            status_code=403,
            detail=f"This invitation was sent to {invite.email}."
        )

    await repo.accept_invite(invite, current_user)

    # Audit log
    audit = AuditRepository(db)
    await audit.log(
        AuditEventType.MEMBER_JOINED,
        actor_user_id=current_user.id,
        fleet_id=invite.fleet_id,
        subject_id=current_user.email,
        metadata={"role": invite.role, "invite_id": str(invite.id)},
    )

    return MemberOut(
        id=current_user.id, email=current_user.email, full_name=current_user.full_name,
        role=current_user.role, is_active=current_user.is_active, created_at=current_user.created_at,
    )


# ─────────────────────────────────────────────────────────────────────────
# Plan / Billing
# ─────────────────────────────────────────────────────────────────────────

@fleet_router.get("/me/plan", response_model=PlanSummary)
async def get_plan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    fleet_repo = FleetRepository(db)
    fleet = await fleet_repo.get(current_user.fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")
    summary = await build_plan_summary(fleet, db)
    return PlanSummary(
        subscription_tier=summary["subscription_tier"],
        plan_label=summary["plan_label"],
        trial_active=summary["trial_active"],
        trial_expired=summary["trial_expired"],
        trial_days_remaining=summary["trial_days_remaining"],
        trial_ends_at=summary["trial_ends_at"],
        limits=PlanLimits(**summary["limits"]),
        usage=PlanUsage(**summary["usage"]),
        features=PlanFeatures(**summary["features"]),
    )


@fleet_router.post("/me/upgrade", response_model=PlanSummary, dependencies=[Depends(require_owner)])
async def upgrade_subscription(
    payload: SubscriptionUpgrade,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Direct tier upgrade (no Stripe). Use POST /billing/checkout for the
    production Stripe-verified path.
    """
    valid_tiers = {"tier2": SubscriptionTier.tier2, "tier3": SubscriptionTier.tier3}
    new_tier = valid_tiers.get(payload.new_tier)
    if not new_tier:
        raise HTTPException(status_code=400, detail=f"Invalid tier '{payload.new_tier}'.")

    fleet_repo = FleetRepository(db)
    fleet = await fleet_repo.get(current_user.fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")

    tier_order = {SubscriptionTier.tier1: 1, SubscriptionTier.tier2: 2, SubscriptionTier.tier3: 3}
    if tier_order[new_tier] <= tier_order[fleet.subscription_tier]:
        raise HTTPException(status_code=400, detail="Cannot downgrade or stay at current tier.")

    old_tier = fleet.subscription_tier.value
    fleet.subscription_tier = new_tier
    fleet.trial_ends_at = None
    await db.commit()
    await db.refresh(fleet)

    # Audit log
    audit = AuditRepository(db)
    await audit.log(
        AuditEventType.TIER_UPGRADED,
        actor_user_id=current_user.id,
        fleet_id=current_user.fleet_id,
        metadata={"from": old_tier, "to": payload.new_tier, "via": "direct"},
    )

    # Confirmation email
    tier_label = get_limits(new_tier)["label"]
    await _run_audit(
        _email.send_tier_upgrade_confirmation(
            to_email=current_user.email,
            fleet_name=fleet.name,
            new_tier_label=tier_label,
        )
    )

    summary = await build_plan_summary(fleet, db)
    return PlanSummary(
        subscription_tier=summary["subscription_tier"],
        plan_label=summary["plan_label"],
        trial_active=summary["trial_active"],
        trial_expired=summary["trial_expired"],
        trial_days_remaining=summary["trial_days_remaining"],
        trial_ends_at=summary["trial_ends_at"],
        limits=PlanLimits(**summary["limits"]),
        usage=PlanUsage(**summary["usage"]),
        features=PlanFeatures(**summary["features"]),
    )
