"""
Fleet endpoints: create fleet (and assign user to it), get my fleet.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User
from app.repositories.repositories import FleetRepository, UserRepository
from app.schemas.schemas import FleetCreate, FleetOut

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
    fleet = await fleet_repo.create(
        name=payload.name,
        country=payload.country,
        subscription_tier=payload.subscription_tier,
    )

    user_repo = UserRepository(db)
    await user_repo.set_fleet(current_user, fleet.id)

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
