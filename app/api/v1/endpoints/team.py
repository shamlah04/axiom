"""
app/api/v1/endpoints/team.py
──────────────────────────────
Phase 3 — Team Management & Subscription API routes.

Routes:
  GET    /team/members                   — List all fleet members + roles
  DELETE /team/members/{user_id}         — Remove member (owner only)
  PATCH  /team/members/{user_id}/role    — Change member role (owner only)

  POST   /team/invites                   — Send invite (owner, tier2+)
  GET    /team/invites                   — List invites (owner only)
  DELETE /team/invites/{invite_id}       — Revoke invite (owner only)
  POST   /team/invites/accept            — Accept invite (public — no auth required)

  GET    /fleets/me/plan                 — Full plan/billing summary
  POST   /fleets/me/upgrade              — Self-serve tier upgrade
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_fleet_user, get_current_user
from app.core.roles import require_owner, require_dispatcher_or_above
from app.core.tier_limits import (
    enforce_intelligence_tier,
    enforce_team_invite_tier,
    build_plan_summary,
    get_limits,
)
from app.models.models import User, SubscriptionTier
from app.models.team import UserRole, InviteStatus
from app.repositories.team_repository import TeamRepository
from app.repositories.repositories import FleetRepository, UserRepository
from app.schemas.team import (
    InviteCreate,
    InviteAccept,
    InviteOut,
    MemberOut,
    MemberRoleUpdate,
    PlanSummary,
    PlanLimits,
    PlanUsage,
    PlanFeatures,
    SubscriptionUpgrade,
)

team_router = APIRouter(prefix="/team", tags=["Team"])
fleet_router = APIRouter(prefix="/fleets", tags=["Fleets"])


# ─────────────────────────────────────────────────────────────────────────
# Team Members
# ─────────────────────────────────────────────────────────────────────────

@team_router.get("/members", response_model=list[MemberOut])
async def list_members(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """List all active members of the fleet with their roles."""
    repo = TeamRepository(db)
    members = await repo.list_members(current_user.fleet_id)
    return [
        MemberOut(
            id=m.id,
            email=m.email,
            full_name=m.full_name,
            role=UserRole(m.role),
            is_active=m.is_active,
            created_at=m.created_at,
        )
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
    """Change a team member's role. Owner only. Cannot demote yourself."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot change your own role. Ask another owner to do this."
        )
    repo = TeamRepository(db)
    user = await repo.update_member_role(current_user.fleet_id, user_id, payload.role)
    if not user:
        raise HTTPException(status_code=404, detail="Member not found in this fleet")
    return MemberOut(
        id=user.id, email=user.email, full_name=user.full_name,
        role=UserRole(user.role), is_active=user.is_active, created_at=user.created_at,
    )


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
    """Remove a member from the fleet. Owner only. Cannot remove yourself."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove yourself from the fleet."
        )
    repo = TeamRepository(db)
    removed = await repo.remove_member(current_user.fleet_id, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found in this fleet")


# ─────────────────────────────────────────────────────────────────────────
# Invites
# ─────────────────────────────────────────────────────────────────────────

@team_router.post(
    "/invites",
    response_model=InviteOut,
    status_code=201,
    dependencies=[
        Depends(require_owner),
        Depends(enforce_team_invite_tier),
    ],
)
async def create_invite(
    payload: InviteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Send a team invitation. Requires owner role + tier2 or higher.

    - Idempotent: re-inviting same email revokes old invite and issues fresh token
    - Cannot invite existing fleet members
    - Cannot invite with 'owner' role (promote existing members instead)
    """
    if payload.role == UserRole.owner:
        raise HTTPException(
            status_code=400,
            detail="Cannot invite with 'owner' role. Invite as dispatcher or viewer, then promote."
        )

    # Check member limit
    fleet_repo = FleetRepository(db)
    fleet = await fleet_repo.get(current_user.fleet_id)
    limits = get_limits(fleet.subscription_tier)

    team_repo = TeamRepository(db)
    members = await team_repo.list_members(current_user.fleet_id)
    pending = await team_repo.list_invites(current_user.fleet_id, status=InviteStatus.pending)

    # Count seats used (existing members + pending invites)
    total_seats_used = len(members) + len(pending)
    if total_seats_used >= limits["max_team_members"]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Team member limit reached for {limits['label']}. "
                f"Max {limits['max_team_members']} members (including pending invites). "
                "Upgrade your plan to add more team members."
            ),
        )

    # Check if already a member
    existing_member = next(
        (m for m in members if m.email == payload.email), None
    )
    if existing_member:
        raise HTTPException(
            status_code=409,
            detail=f"{payload.email} is already a member of this fleet."
        )

    invite = await team_repo.create_invite(
        fleet_id=current_user.fleet_id,
        invited_by=current_user.id,
        email=payload.email,
        role=payload.role,
    )
    return invite


@team_router.get(
    "/invites",
    response_model=list[InviteOut],
    dependencies=[Depends(require_owner)],
)
async def list_invites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """List all invites for the fleet. Owner only."""
    repo = TeamRepository(db)
    # Clean up stale invites before returning
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
    """Revoke a pending invite. Owner only."""
    repo = TeamRepository(db)
    # Verify invite belongs to this fleet
    invites = await repo.list_invites(current_user.fleet_id)
    if not any(i.id == invite_id for i in invites):
        raise HTTPException(status_code=404, detail="Invite not found")
    await repo.revoke_invite(invite_id)


@team_router.post("/invites/accept", response_model=MemberOut)
async def accept_invite(
    payload: InviteAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),  # must be logged in, but no fleet required
):
    """
    Accept a team invitation. User must be authenticated.

    - If user already has a fleet, returns 409
    - If token is invalid/expired/revoked, returns 400
    - On success: sets user.fleet_id and user.role
    """
    if current_user.fleet_id:
        raise HTTPException(
            status_code=409,
            detail="You are already a member of a fleet. Leave your current fleet before accepting an invite."
        )

    repo = TeamRepository(db)
    invite = await repo.get_invite_by_token(payload.token)

    if not invite:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation token.")

    if invite.status == InviteStatus.revoked:
        raise HTTPException(status_code=400, detail="This invitation has been revoked.")

    if invite.status == InviteStatus.accepted:
        raise HTTPException(status_code=400, detail="This invitation has already been used.")

    if invite.status == InviteStatus.expired:
        raise HTTPException(status_code=400, detail="This invitation has expired. Ask your fleet owner to send a new invite.")

    # Check expiry
    now = datetime.now(timezone.utc)
    exp = invite.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if now > exp:
        invite.status = InviteStatus.expired
        await db.commit()
        raise HTTPException(status_code=400, detail="This invitation has expired.")

    # Check email match
    if current_user.email.lower() != invite.email.lower():
        raise HTTPException(
            status_code=403,
            detail=f"This invitation was sent to {invite.email}. Please log in with that account."
        )

    updated_invite = await repo.accept_invite(invite, current_user)

    return MemberOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=UserRole(current_user.role),
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


# ─────────────────────────────────────────────────────────────────────────
# Plan / Billing
# ─────────────────────────────────────────────────────────────────────────

@fleet_router.get("/me/plan", response_model=PlanSummary)
async def get_plan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Full subscription plan summary for the fleet.
    Shows tier, limits, current usage, trial status, and feature flags.
    Used by the billing/settings page.
    """
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


@fleet_router.post(
    "/me/upgrade",
    response_model=PlanSummary,
    dependencies=[Depends(require_owner)],
)
async def upgrade_subscription(
    payload: SubscriptionUpgrade,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Self-serve subscription upgrade.

    Phase 3: Direct DB update (no payment verification).
    Phase 4: This endpoint will be replaced by Stripe webhook handler.
             The UI will redirect to Stripe Checkout, and on success
             Stripe calls our webhook which upgrades the tier.

    Allowed upgrades:
      tier1 → tier2
      tier1 → tier3
      tier2 → tier3

    Downgrades are not permitted via API (contact support).
    """
    valid_tiers = {"tier2": SubscriptionTier.tier2, "tier3": SubscriptionTier.tier3}
    new_tier = valid_tiers.get(payload.new_tier)

    if not new_tier:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier '{payload.new_tier}'. Must be 'tier2' or 'tier3'."
        )

    fleet_repo = FleetRepository(db)
    fleet = await fleet_repo.get(current_user.fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")

    tier_order = {
        SubscriptionTier.tier1: 1,
        SubscriptionTier.tier2: 2,
        SubscriptionTier.tier3: 3,
    }
    if tier_order[new_tier] <= tier_order[fleet.subscription_tier]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot downgrade or stay at same tier. "
                f"Current: {fleet.subscription_tier.value}. Requested: {payload.new_tier}."
            )
        )

    fleet.subscription_tier = new_tier
    fleet.trial_ends_at = None  # Clear trial on upgrade
    await db.commit()
    await db.refresh(fleet)

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
