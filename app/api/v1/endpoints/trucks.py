"""
app/api/v1/endpoints/trucks.py  — with tier enforcement on POST
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
from app.core.tier_limits import enforce_truck_limit
from app.models.models import User
from app.repositories.repositories import TruckRepository
from app.schemas.schemas import TruckCreate, TruckUpdate, TruckOut

router = APIRouter(prefix="/trucks", tags=["Trucks"])


@router.get("", response_model=list[TruckOut])
async def list_trucks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = TruckRepository(db)
    return await repo.list_by_fleet(current_user.fleet_id)


@router.post(
    "",
    response_model=TruckOut,
    status_code=201,
    dependencies=[Depends(enforce_truck_limit)],   # ← tier check runs first
)
async def create_truck(
    payload: TruckCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = TruckRepository(db)
    return await repo.create(fleet_id=current_user.fleet_id, **payload.model_dump())


@router.get("/{truck_id}", response_model=TruckOut)
async def get_truck(
    truck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = TruckRepository(db)
    truck = await repo.get(truck_id, current_user.fleet_id)
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    return truck


@router.patch("/{truck_id}", response_model=TruckOut)
async def update_truck(
    truck_id: uuid.UUID,
    payload: TruckUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = TruckRepository(db)
    truck = await repo.get(truck_id, current_user.fleet_id)
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    return await repo.update(truck, payload.model_dump(exclude_unset=True))


@router.delete("/{truck_id}", status_code=204)
async def delete_truck(
    truck_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """Soft-delete: sets is_active=False. Jobs referencing the truck are preserved."""
    repo = TruckRepository(db)
    truck = await repo.get(truck_id, current_user.fleet_id)
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    await repo.update(truck, {"is_active": False})
