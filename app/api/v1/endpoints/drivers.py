"""
Driver endpoints: list and create.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
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


@router.post("", response_model=DriverOut, status_code=201)
async def create_driver(
    payload: DriverCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = DriverRepository(db)
    return await repo.create(
        fleet_id=current_user.fleet_id,
        **payload.model_dump(),
    )
