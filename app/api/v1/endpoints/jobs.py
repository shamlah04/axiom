"""
Jobs endpoints: create+predict, list, get, status update, actual update.
Phase 1: ML-backed prediction and audit logging.
"""
import uuid

import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.core.deps import get_current_fleet_user
from app.core.roles import require_dispatcher_or_above
from app.ml.features import JobFeatureInput
from app.ml.prediction_engine import ml_engine
from app.ml.model_registry import registry
from app.models.models import User, Job
from app.models.ml_models import PredictionLog
from app.models.audit import AuditEventType
from app.repositories.repositories import JobRepository, TruckRepository, DriverRepository
from app.repositories.ml_repository import PredictionLogRepository, MLModelVersionRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.schemas import (
    JobCreate, JobOut, JobPredictionResult, JobStatusUpdate, JobActualUpdate
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


async def _run_audit(coro):
    """If in test mode, wait for the audit task to finish to avoid race conditions."""
    if settings.TESTING:
        await coro
    else:
        asyncio.create_task(coro)


async def _log_audit(event_type: str, actor_id=None, fleet_id=None, subject_id=None, metadata=None, ip=None):
    """Background task for auditing."""
    async with AsyncSessionLocal() as db:
        audit = AuditRepository(db)
        await audit.log(
            event_type,
            actor_user_id=actor_id,
            fleet_id=fleet_id,
            subject_id=subject_id,
            metadata=metadata,
            ip_address=ip
        )


@router.post(
    "",
    response_model=JobPredictionResult,
    status_code=201,
    dependencies=[Depends(require_dispatcher_or_above)],
)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    truck_repo = TruckRepository(db)
    driver_repo = DriverRepository(db)
    job_repo = JobRepository(db)
    log_repo = PredictionLogRepository(db)

    truck = await truck_repo.get(payload.truck_id, current_user.fleet_id)
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")

    driver = await driver_repo.get(payload.driver_id, current_user.fleet_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    # --- Build feature input ---
    feature_input = JobFeatureInput(
        distance_km=payload.distance_km,
        estimated_duration_hours=payload.estimated_duration_hours,
        offered_rate=payload.offered_rate,
        toll_costs=payload.toll_costs,
        other_costs=payload.other_costs,
        fuel_price_per_unit=payload.fuel_price_per_unit,
        fuel_consumption_per_100km=truck.fuel_consumption_per_100km,
        maintenance_cost_per_km=truck.maintenance_cost_per_km,
        insurance_monthly=truck.insurance_monthly,
        leasing_monthly=truck.leasing_monthly or 0.0,
        fuel_type=truck.fuel_type.value,
        hourly_rate=driver.hourly_rate,
        monthly_fixed_cost=driver.monthly_fixed_cost,
    )

    # --- Run prediction (ML or deterministic fallback) ---
    prediction = ml_engine.predict(feature_input, offered_rate=payload.offered_rate)

    # --- Persist job ---
    job = Job(
        id=uuid.uuid4(),
        fleet_id=current_user.fleet_id,
        truck_id=payload.truck_id,
        driver_id=payload.driver_id,
        origin=payload.origin,
        destination=payload.destination,
        distance_km=payload.distance_km,
        estimated_duration_hours=payload.estimated_duration_hours,
        offered_rate=payload.offered_rate,
        toll_costs=payload.toll_costs,
        fuel_price_per_unit=payload.fuel_price_per_unit,
        other_costs=payload.other_costs,
        total_cost=prediction.predicted_total_cost,
        net_profit=prediction.predicted_net_profit,
        margin_pct=prediction.margin_pct,
        risk_level=prediction.risk_level,
        recommendation=prediction.recommendation,
        ai_explanation=prediction.explanation,
        status="pending",
        job_date=payload.job_date,
    )
    db.add(job)
    await db.flush()  # get job.id before creating log

    # --- Persist prediction log ---
    version_repo = MLModelVersionRepository(db)
    active_version = await version_repo.get_active()

    from app.ml.features import build_feature_vector, FEATURE_NAMES
    X = build_feature_vector(feature_input)
    features_dict = {name: float(val) for name, val in zip(FEATURE_NAMES, X.flatten())}

    pred_log = PredictionLog(
        job_id=job.id,
        fleet_id=current_user.fleet_id,
        model_version_id=active_version.id if active_version else None,
        used_ml_model=prediction.used_ml_model,
        predicted_net_profit=prediction.predicted_net_profit,
        predicted_total_cost=prediction.predicted_total_cost,
        predicted_margin_pct=prediction.margin_pct,
        feature_importances=prediction.feature_importances,
        features_snapshot=features_dict,
    )
    await log_repo.create(pred_log)

    await db.commit()

    return JobPredictionResult(
        job_id=job.id,
        total_cost=prediction.predicted_total_cost,
        net_profit=prediction.predicted_net_profit,
        margin_pct=prediction.margin_pct,
        risk_level=prediction.risk_level,
        recommendation=prediction.recommendation,
        ai_explanation=prediction.explanation,
        # Cost breakdown
        fuel_cost=_get_fuel_cost(feature_input),
        driver_cost=_get_driver_cost(feature_input),
        maintenance_cost=feature_input.distance_km * feature_input.maintenance_cost_per_km,
        toll_costs=payload.toll_costs,
        fixed_cost_allocation=_get_fixed_allocation(feature_input),
        other_costs=payload.other_costs,
    )


@router.get("", response_model=list[JobOut])
async def list_jobs(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    job_repo = JobRepository(db)
    return await job_repo.list_by_fleet(current_user.fleet_id, limit=limit, offset=offset)


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = JobRepository(db)
    job = await repo.get(job_id, current_user.fleet_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch(
    "/{job_id}/status",
    response_model=JobOut,
    dependencies=[Depends(require_dispatcher_or_above)],
)
async def update_job_status(
    job_id: uuid.UUID,
    payload: JobStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    valid_statuses = {"accepted", "rejected", "completed", "pending"}
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")

    job_repo = JobRepository(db)
    job = await job_repo.update_status(job_id, current_user.fleet_id, payload.status)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Audit for terminal states
    if payload.status in ("accepted", "rejected"):
        event = AuditEventType.JOB_ACCEPTED if payload.status == "accepted" else AuditEventType.JOB_REJECTED
        await _run_audit(
            _log_audit(
                event,
                actor_id=current_user.id,
                fleet_id=current_user.fleet_id,
                subject_id=str(job_id),
                metadata={
                    "status": payload.status,
                    "net_profit": job.net_profit,
                    "margin_pct": job.margin_pct,
                    "recommendation": job.recommendation,
                }
            )
        )

    return job


@router.patch(
    "/{job_id}/actual",
    response_model=JobOut,
    dependencies=[Depends(require_dispatcher_or_above)],
)
async def update_job_actual(
    job_id: uuid.UUID,
    payload: JobActualUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Record actual revenue and cost after job completion.
    Also updates the PredictionLog with error metrics for model monitoring.
    """
    job_repo = JobRepository(db)
    log_repo = PredictionLogRepository(db)

    job = await job_repo.update_actual(
        job_id, current_user.fleet_id, payload.actual_revenue, payload.actual_cost
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # --- Update prediction log with actual error ---
    actual_net_profit = payload.actual_revenue - payload.actual_cost
    predicted_net_profit_at_creation = job.net_profit # Captured before update_actual

    await log_repo.update_actuals(
        job_id=job_id,
        actual_net_profit=actual_net_profit,
        actual_total_cost=payload.actual_cost,
        offered_rate=job.offered_rate,
    )

    # Audit log
    await _run_audit(
        _log_audit(
            AuditEventType.JOB_ACTUALS_RECORDED,
            actor_id=current_user.id,
            fleet_id=current_user.fleet_id,
            subject_id=str(job_id),
            metadata={
                "actual_revenue": payload.actual_revenue,
                "actual_cost": payload.actual_cost,
                "actual_net_profit": actual_net_profit,
                "predicted_net_profit": predicted_net_profit_at_creation,
            }
        )
    )

    return job


@router.get("/{job_id}/explanation")
async def get_job_explanation(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """
    Returns feature importances for a specific job prediction.
    Powers the 'Why this prediction?' UI component.
    """
    log_repo = PredictionLogRepository(db)
    pred_log = await log_repo.get_by_job_id(job_id)
    if not pred_log:
        raise HTTPException(status_code=404, detail="No prediction log found for this job")

    # Sort by importance descending
    importances = pred_log.feature_importances or {}
    sorted_importances = dict(
        sorted(importances.items(), key=lambda x: -x[1])
    )

    return {
        "job_id": str(job_id),
        "used_ml_model": pred_log.used_ml_model,
        "predicted_net_profit": pred_log.predicted_net_profit,
        "predicted_margin_pct": pred_log.predicted_margin_pct,
        "actual_net_profit": pred_log.actual_net_profit,
        "profit_error": pred_log.profit_error,
        "profit_error_pct": pred_log.profit_error_pct,
        "feature_importances": sorted_importances,
    }


# ---------------------------------------------------------------------------
# Internal cost helpers
# ---------------------------------------------------------------------------

def _get_fuel_cost(fi: JobFeatureInput) -> float:
    return (fi.distance_km / 100.0) * fi.fuel_consumption_per_100km * fi.fuel_price_per_unit

def _get_driver_cost(fi: JobFeatureInput) -> float:
    return fi.hourly_rate * fi.estimated_duration_hours + fi.monthly_fixed_cost / (22 * 8)

def _get_fixed_allocation(fi: JobFeatureInput) -> float:
    avg_monthly_km = 350.0 * 22
    return (fi.insurance_monthly + fi.leasing_monthly) / avg_monthly_km * fi.distance_km
