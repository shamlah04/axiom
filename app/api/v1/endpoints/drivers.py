"""
app/api/v1/endpoints/drivers.py  — with tier enforcement on POST
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
from app.core.roles import require_dispatcher_or_above
from app.core.tier_limits import enforce_driver_limit
from app.models.models import User
from app.repositories.repositories import DriverRepository
from app.schemas.schemas import DriverCreate, DriverOut

router = APIRouter(prefix="/drivers", tags=["Drivers"])


@router.get("", response_model=list[DriverOut])
async def list_drivers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = DriverRepository(db)
    return await repo.list_by_fleet(current_user.fleet_id)


@router.post(
    "",
    response_model=DriverOut,
    status_code=201,
    dependencies=[
        Depends(enforce_driver_limit),
        Depends(require_dispatcher_or_above),
    ],
)
async def create_driver(
    payload: DriverCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = DriverRepository(db)
    return await repo.create(fleet_id=current_user.fleet_id, **payload.model_dump())


@router.get("/{driver_id}", response_model=DriverOut)
async def get_driver(
    driver_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = DriverRepository(db)
    driver = await repo.get(driver_id, current_user.fleet_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver


@router.delete(
    "/{driver_id}",
    status_code=204,
    dependencies=[Depends(require_dispatcher_or_above)],
)
async def delete_driver(
    driver_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """Soft-delete: sets is_active=False. Jobs referencing the driver are preserved."""
    repo = DriverRepository(db)
    driver = await repo.get(driver_id, current_user.fleet_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    await repo.update(driver, {"is_active": False})
