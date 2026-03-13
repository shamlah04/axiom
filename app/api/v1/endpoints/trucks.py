"""
app/api/v1/endpoints/trucks.py  — with audit coverage added
─────────────────────────────────────────────────────────────
CHANGES vs existing:
  • POST /trucks  → audit TRUCK_ADDED
  • PATCH /trucks/{id} → audit TRUCK_UPDATED
  • DELETE /trucks/{id} → audit TRUCK_REMOVED

New AuditEventType values needed in app/models/audit.py (see audit_additions.py).
"""
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import get_current_fleet_user
from app.core.roles import require_dispatcher_or_above
from app.core.tier_limits import enforce_truck_limit
from app.core.config import settings
from app.models.models import User
from app.models.audit import AuditEventType
from app.repositories.repositories import TruckRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.schemas import TruckCreate, TruckUpdate, TruckOut

router = APIRouter(prefix="/trucks", tags=["Trucks"])


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
    dependencies=[
        Depends(enforce_truck_limit),
        Depends(require_dispatcher_or_above),
    ],
)
async def create_truck(
    payload: TruckCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = TruckRepository(db)
    truck = await repo.create(fleet_id=current_user.fleet_id, **payload.model_dump())

    # ── AUDIT ──
    await _run_audit(
        _log_audit(
            AuditEventType.TRUCK_ADDED,
            actor_id=current_user.id,
            fleet_id=current_user.fleet_id,
            subject_id=truck.id,
            metadata={"name": truck.name, "fuel_type": truck.fuel_type.value},
        )
    )

    return truck


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


@router.patch(
    "/{truck_id}",
    response_model=TruckOut,
    dependencies=[Depends(require_dispatcher_or_above)],
)
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

    changes = payload.model_dump(exclude_unset=True)
    updated = await repo.update(truck, changes)

    # ── AUDIT ──
    await _run_audit(
        _log_audit(
            AuditEventType.TRUCK_UPDATED,
            actor_id=current_user.id,
            fleet_id=current_user.fleet_id,
            subject_id=truck_id,
            metadata={"truck_name": truck.name, "fields_changed": list(changes.keys())},
        )
    )

    return updated


@router.delete(
    "/{truck_id}",
    status_code=204,
    dependencies=[Depends(require_dispatcher_or_above)],
)
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

    # ── AUDIT ──
    await _run_audit(
        _log_audit(
            AuditEventType.TRUCK_REMOVED,
            actor_id=current_user.id,
            fleet_id=current_user.fleet_id,
            subject_id=truck_id,
            metadata={"truck_name": truck.name},
        )
    )
