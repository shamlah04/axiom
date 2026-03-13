"""
Fleet endpoints: create fleet (and assign user to it), get my fleet.
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User, SubscriptionTier
import asyncio
from app.repositories.repositories import FleetRepository, UserRepository
from app.repositories.audit_repository import AuditRepository
from app.models.audit import AuditEventType
from app.services.email_service import EmailService
from app.schemas.schemas import FleetCreate, FleetOut

_email = EmailService()

router = APIRouter(prefix="/fleets", tags=["Fleets"])


@router.post("", response_model=FleetOut, status_code=201)
async def create_fleet(
    payload: FleetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.fleet_id:
        raise HTTPException(status_code=400, detail="User already belongs to a fleet")

    fleet_repo = FleetRepository(db)

    # Tier1 fleets get a 14-day trial
    trial_ends_at = None
    if payload.subscription_tier == SubscriptionTier.tier1:
        trial_ends_at = datetime.now(timezone.utc) + timedelta(days=14)

    fleet = await fleet_repo.create(
        name=payload.name,
        country=payload.country,
        subscription_tier=payload.subscription_tier,
        trial_ends_at=trial_ends_at,
    )

    user_repo = UserRepository(db)
    await user_repo.set_fleet(current_user, fleet.id, role="owner")

    # Audit
    audit = AuditRepository(db)
    # Log fleet creation
    await audit.log(
        AuditEventType.FLEET_CREATED,
        actor_user_id=current_user.id,
        fleet_id=fleet.id,
        metadata={
            "fleet_name": fleet.name,
            "country": fleet.country,
            "tier": fleet.subscription_tier.value,
        },
    )

    # Log trial start
    if fleet.trial_ends_at:
        await audit.log(
            AuditEventType.TRIAL_STARTED,
            actor_user_id=current_user.id,
            fleet_id=fleet.id,
            metadata={
                "fleet_name": fleet.name,
                "tier": fleet.subscription_tier.value,
                "trial_ends_at": fleet.trial_ends_at.isoformat(),
            },
        )

    # Send fleet-created confirmation (fire-and-forget)
    asyncio.create_task(
        _email.send_fleet_created(
            to_email=current_user.email,
            full_name=current_user.full_name or current_user.email,
            fleet_name=fleet.name,
            trial_days=14,
        )
    )

    return fleet


@router.get("/me", response_model=FleetOut)
async def get_my_fleet(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.fleet_id:
        raise HTTPException(status_code=404, detail="User is not associated with any fleet")

    fleet_repo = FleetRepository(db)
    fleet = await fleet_repo.get(current_user.fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")
    return fleet
