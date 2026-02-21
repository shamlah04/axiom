"""
app/core/tier_limits.py

Subscription tier enforcement.
Defines per-tier limits and provides FastAPI dependencies
that enforce them before resource creation.

Usage in endpoints:
    @router.post("", ...)
    async def create_truck(
        ...,
        _: None = Depends(enforce_truck_limit),
    ):
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
from app.models.models import User, Truck, Driver, SubscriptionTier


# ---------------------------------------------------------------------------
# Tier limit definitions
# ---------------------------------------------------------------------------

TIER_LIMITS: dict[SubscriptionTier, dict] = {
    SubscriptionTier.tier1: {
        "max_trucks":  2,
        "max_drivers": 5,
        "label": "Tier 1 (1–2 trucks)",
    },
    SubscriptionTier.tier2: {
        "max_trucks":  10,
        "max_drivers": 25,
        "label": "Tier 2 (3–10 trucks)",
    },
    SubscriptionTier.tier3: {
        "max_trucks":  999,   # effectively unlimited
        "max_drivers": 999,
        "label": "Tier 3 (Enterprise)",
    },
}


def _get_limits(tier: SubscriptionTier) -> dict:
    return TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.tier1])


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


# ---------------------------------------------------------------------------
# Truck limit dependency
# ---------------------------------------------------------------------------

async def enforce_truck_limit(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
) -> None:
    """
    Raises HTTP 403 if the fleet has reached its truck limit for the
    current subscription tier.
    Inject as a dependency on POST /trucks.
    """
    from app.repositories.repositories import FleetRepository

    fleet_repo = FleetRepository(db)
    fleet = await fleet_repo.get_by_id(current_user.fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")

    limits = _get_limits(fleet.subscription_tier)
    max_trucks = limits["max_trucks"]
    current_count = await _count_active(db, Truck, current_user.fleet_id)

    if current_count >= max_trucks:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Truck limit reached for your plan ({limits['label']}). "
                f"You have {current_count}/{max_trucks} active trucks. "
                f"Upgrade your subscription to add more."
            ),
        )


# ---------------------------------------------------------------------------
# Driver limit dependency
# ---------------------------------------------------------------------------

async def enforce_driver_limit(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
) -> None:
    """
    Raises HTTP 403 if the fleet has reached its driver limit.
    Inject as a dependency on POST /drivers.
    """
    from app.repositories.repositories import FleetRepository

    fleet_repo = FleetRepository(db)
    fleet = await fleet_repo.get_by_id(current_user.fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")

    limits = _get_limits(fleet.subscription_tier)
    max_drivers = limits["max_drivers"]
    current_count = await _count_active(db, Driver, current_user.fleet_id)

    if current_count >= max_drivers:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Driver limit reached for your plan ({limits['label']}). "
                f"You have {current_count}/{max_drivers} active drivers. "
                f"Upgrade your subscription to add more."
            ),
        )
