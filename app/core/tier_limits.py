"""
app/core/tier_limits.py  [Phase 3 update]
──────────────────────────────────────────
Subscription tier enforcement — resource limits AND feature gates.

Phase 1/2 added: enforce_truck_limit, enforce_driver_limit
Phase 3 adds:
  - require_minimum_tier(tier)  → feature-level access gate
  - is_trial_expired(fleet)     → trial expiry check
  - get_plan_summary(fleet)     → what the fleet can/cannot do
  - enforce_intelligence_tier   → gates Phase 2 intelligence endpoints
  - enforce_team_invite_tier    → gates team invite (tier2+)
  - Hardened is_sqlite() helper

Usage:
    @router.get("/intelligence/benchmark")
    async def get_benchmark(
        _: None = Depends(enforce_intelligence_tier),
        ...
    ):
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
from app.models.models import User, Fleet, Truck, Driver, SubscriptionTier
from app.repositories.repositories import FleetRepository


# ---------------------------------------------------------------------------
# Tier limit definitions (resource caps)
# ---------------------------------------------------------------------------

TIER_LIMITS: dict[SubscriptionTier, dict] = {
    SubscriptionTier.tier1: {
        "max_trucks":         2,
        "max_drivers":        5,
        "max_team_members":   1,      # owner only
        "intelligence":       False,  # Phase 2 analytics
        "team_invites":       False,  # cannot invite others
        "trial_days":         14,
        "label": "Starter (1–2 trucks)",
    },
    SubscriptionTier.tier2: {
        "max_trucks":         10,
        "max_drivers":        25,
        "max_team_members":   5,
        "intelligence":       True,
        "team_invites":       True,
        "trial_days":         None,   # paid tier, no trial
        "label": "Growth (3–10 trucks)",
    },
    SubscriptionTier.tier3: {
        "max_trucks":         999,
        "max_drivers":        999,
        "max_team_members":   999,
        "intelligence":       True,
        "team_invites":       True,
        "trial_days":         None,
        "label": "Enterprise",
    },
}


def get_limits(tier: SubscriptionTier) -> dict:
    return TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.tier1])


# ---------------------------------------------------------------------------
# SQLite detection utility (hardened vs Phase 2's db.bind approach)
# ---------------------------------------------------------------------------

def is_sqlite(db: AsyncSession) -> bool:
    """
    Safe dialect detection that works with async SQLAlchemy.
    Uses the engine URL string rather than accessing db.bind (which can be None).
    """
    try:
        url = str(db.get_bind().engine.url)
        return "sqlite" in url
    except Exception:
        # Fallback: check sync_session's bind
        try:
            return "sqlite" in str(db.sync_session.bind.dialect.name)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Trial expiry helper
# ---------------------------------------------------------------------------

def is_trial_expired(fleet: Fleet) -> bool:
    """
    Returns True if the fleet is on tier1 with an expired trial.
    tier2/tier3 fleets never expire this way.
    """
    if fleet.subscription_tier != SubscriptionTier.tier1:
        return False
    if fleet.trial_ends_at is None:
        return False
    now = datetime.now(timezone.utc)
    end = fleet.trial_ends_at
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return now > end


# ---------------------------------------------------------------------------
# Generic limit checker
# ---------------------------------------------------------------------------

async def _count_active(db: AsyncSession, model, fleet_id) -> int:
    result = await db.execute(
        select(func.count(model.id)).where(
            model.fleet_id == fleet_id,
            model.is_active == True,
        )
    )
    return result.scalar() or 0


async def _get_fleet_or_403(db: AsyncSession, fleet_id) -> Fleet:
    repo = FleetRepository(db)
    fleet = await repo.get(fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")
    return fleet


# ---------------------------------------------------------------------------
# Resource limit dependencies (existing, now refactored)
# ---------------------------------------------------------------------------

async def enforce_truck_limit(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
) -> None:
    fleet = await _get_fleet_or_403(db, current_user.fleet_id)
    limits = get_limits(fleet.subscription_tier)
    current = await _count_active(db, Truck, current_user.fleet_id)
    if current >= limits["max_trucks"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Truck limit reached for your plan ({limits['label']}). "
                f"{current}/{limits['max_trucks']} active trucks. "
                "Upgrade to add more."
            ),
        )


async def enforce_driver_limit(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
) -> None:
    fleet = await _get_fleet_or_403(db, current_user.fleet_id)
    limits = get_limits(fleet.subscription_tier)
    current = await _count_active(db, Driver, current_user.fleet_id)
    if current >= limits["max_drivers"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Driver limit reached for your plan ({limits['label']}). "
                f"{current}/{limits['max_drivers']} active drivers. "
                "Upgrade to add more."
            ),
        )


# ---------------------------------------------------------------------------
# Feature gate dependencies (Phase 3)
# ---------------------------------------------------------------------------

def require_minimum_tier(minimum: SubscriptionTier):
    """
    Returns a FastAPI dependency that enforces a minimum subscription tier.

    Usage:
        @router.get("/intelligence/benchmark",
                    dependencies=[Depends(require_minimum_tier(SubscriptionTier.tier2))])
    """
    tier_order = {
        SubscriptionTier.tier1: 1,
        SubscriptionTier.tier2: 2,
        SubscriptionTier.tier3: 3,
    }

    async def _check(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_fleet_user),
    ) -> None:
        fleet = await _get_fleet_or_403(db, current_user.fleet_id)

        # Trial expiry check (tier1 only)
        if is_trial_expired(fleet):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "trial_expired",
                    "message": "Your free trial has ended. Upgrade to continue using Axiom.",
                    "upgrade_url": "/settings/billing",
                },
            )

        if tier_order.get(fleet.subscription_tier, 0) < tier_order.get(minimum, 0):
            min_label = get_limits(minimum)["label"]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "tier_required",
                    "message": f"This feature requires the {min_label} plan or higher.",
                    "current_tier": fleet.subscription_tier.value,
                    "required_tier": minimum.value,
                    "upgrade_url": "/settings/billing",
                },
            )

    return _check


# Pre-built dependency instances for common gates
enforce_intelligence_tier = require_minimum_tier(SubscriptionTier.tier2)
enforce_team_invite_tier   = require_minimum_tier(SubscriptionTier.tier2)
enforce_trial_not_expired  = require_minimum_tier(SubscriptionTier.tier1)


# ---------------------------------------------------------------------------
# Plan summary helper (used by GET /fleets/me/plan)
# ---------------------------------------------------------------------------

async def build_plan_summary(fleet: Fleet, db: AsyncSession) -> dict:
    """
    Returns a full picture of what the fleet can/cannot do.
    Used by the settings → billing page to render the feature matrix.
    """
    limits = get_limits(fleet.subscription_tier)
    truck_count = await _count_active(db, Truck, fleet.id)
    driver_count = await _count_active(db, Driver, fleet.id)

    trial_active = (
        fleet.subscription_tier == SubscriptionTier.tier1
        and fleet.trial_ends_at is not None
        and not is_trial_expired(fleet)
    )
    trial_expired = is_trial_expired(fleet)

    days_remaining = None
    if trial_active and fleet.trial_ends_at:
        end = fleet.trial_ends_at
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        days_remaining = max(0, (end - datetime.now(timezone.utc)).days)

    return {
        "subscription_tier": fleet.subscription_tier.value,
        "plan_label": limits["label"],
        "trial_active": trial_active,
        "trial_expired": trial_expired,
        "trial_days_remaining": days_remaining,
        "trial_ends_at": fleet.trial_ends_at.isoformat() if fleet.trial_ends_at else None,
        "limits": {
            "max_trucks": limits["max_trucks"],
            "max_drivers": limits["max_drivers"],
            "max_team_members": limits["max_team_members"],
        },
        "usage": {
            "trucks": truck_count,
            "drivers": driver_count,
        },
        "features": {
            "intelligence_dashboard": limits["intelligence"],
            "team_invites": limits["team_invites"],
            "ml_predictions": True,       # all tiers
            "scenario_simulator": True,   # all tiers
            "anomaly_detection": limits["intelligence"],
            "trend_analysis": limits["intelligence"],
            "cross_fleet_benchmark": limits["intelligence"],
        },
    }
