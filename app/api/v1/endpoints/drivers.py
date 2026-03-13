"""
app/api/v1/endpoints/drivers.py  — with audit coverage added
──────────────────────────────────────────────────────────────
CHANGES vs existing:
  • POST /drivers  → audit DRIVER_ADDED
  • DELETE /drivers/{id} → audit DRIVER_REMOVED
"""
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import get_current_fleet_user
from app.core.roles import require_dispatcher_or_above
from app.core.tier_limits import enforce_driver_limit
from app.core.config import settings
from app.models.models import User
from app.models.audit import AuditEventType
from app.repositories.repositories import DriverRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.schemas import DriverCreate, DriverOut

router = APIRouter(prefix="/drivers", tags=["Drivers"])


async def _run_audit(coro):
    """If in test mode, wait for the task to finish to avoid race conditions."""
    if settings.TESTING:
        await coro
    else:
        asyncio.create_task(coro)


async def _log_audit(event, actor_id, fleet_id, subject_id=None, metadata=None):
    """Background task for auditing with a fresh session."""
    async with AsyncSessionLocal() as db:
        await AuditRepository(db).log(
            event,
            actor_user_id=actor_id,
            fleet_id=fleet_id,
            subject_id=str(subject_id) if subject_id else None,
            metadata=metadata,
        )


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
    driver = await repo.create(fleet_id=current_user.fleet_id, **payload.model_dump())

    # ── AUDIT ──
    await _run_audit(
        _log_audit(
            AuditEventType.DRIVER_ADDED,
            actor_id=current_user.id,
            fleet_id=current_user.fleet_id,
            subject_id=driver.id,
            metadata={"name": driver.name},
        )
    )

    return driver


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
    repo = DriverRepository(db)
    driver = await repo.get(driver_id, current_user.fleet_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    await repo.update(driver, {"is_active": False})

    # ── AUDIT ──
    await _run_audit(
        _log_audit(
            AuditEventType.DRIVER_REMOVED,
            actor_id=current_user.id,
            fleet_id=current_user.fleet_id,
            subject_id=driver_id,
            metadata={"driver_name": driver.name},
        )
    )
