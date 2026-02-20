"""
Jobs endpoints: create+predict, list, get, status update, actual update.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_fleet_user
from app.models.models import User
from app.repositories.repositories import JobRepository, TruckRepository, DriverRepository
from app.schemas.schemas import (
    JobCreate, JobOut, JobPredictionResult, JobStatusUpdate, JobActualUpdate
)
from app.services.prediction_engine import (
    profit_engine, TruckCostConfig, DriverCostConfig, JobInput
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobPredictionResult, status_code=201)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    truck_repo = TruckRepository(db)
    driver_repo = DriverRepository(db)
    job_repo = JobRepository(db)

    truck = await truck_repo.get(payload.truck_id, current_user.fleet_id)
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")

    driver = await driver_repo.get(payload.driver_id, current_user.fleet_id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    # Run prediction
    prediction = profit_engine.predict(
        job=JobInput(
            distance_km=payload.distance_km,
            estimated_duration_hours=payload.estimated_duration_hours,
            offered_rate=payload.offered_rate,
            toll_costs=payload.toll_costs,
            fuel_price_per_unit=payload.fuel_price_per_unit,
            other_costs=payload.other_costs,
        ),
        truck=TruckCostConfig(
            fuel_consumption_per_100km=truck.fuel_consumption_per_100km,
            maintenance_cost_per_km=truck.maintenance_cost_per_km,
            insurance_monthly=truck.insurance_monthly,
            leasing_monthly=truck.leasing_monthly or 0.0,
        ),
        driver=DriverCostConfig(
            hourly_rate=driver.hourly_rate,
            monthly_fixed_cost=driver.monthly_fixed_cost,
        ),
    )

    # Persist job with prediction results
    job = await job_repo.create(
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
        job_date=payload.job_date,
        total_cost=prediction.total_cost,
        net_profit=prediction.net_profit,
        margin_pct=prediction.margin_pct,
        risk_level=prediction.risk_level,
        recommendation=prediction.recommendation,
        ai_explanation=prediction.explanation,
    )

    bd = prediction.cost_breakdown
    return JobPredictionResult(
        job_id=job.id,
        total_cost=prediction.total_cost,
        net_profit=prediction.net_profit,
        margin_pct=prediction.margin_pct,
        risk_level=prediction.risk_level,
        recommendation=prediction.recommendation,
        ai_explanation=prediction.explanation,
        fuel_cost=bd.fuel_cost,
        driver_cost=bd.driver_cost,
        maintenance_cost=bd.maintenance_cost,
        toll_costs=bd.toll_costs,
        fixed_cost_allocation=bd.fixed_cost_allocation,
        other_costs=bd.other_costs,
    )


@router.get("", response_model=list[JobOut])
async def list_jobs(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    repo = JobRepository(db)
    return await repo.list_by_fleet(current_user.fleet_id, limit=limit, offset=offset)


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


@router.patch("/{job_id}/status", response_model=JobOut)
async def update_job_status(
    job_id: uuid.UUID,
    payload: JobStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    valid_statuses = {"accepted", "rejected", "completed", "pending"}
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")

    repo = JobRepository(db)
    job = await repo.get(job_id, current_user.fleet_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return await repo.update(job, {"status": payload.status})


@router.patch("/{job_id}/actual", response_model=JobOut)
async def update_job_actual(
    job_id: uuid.UUID,
    payload: JobActualUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_fleet_user),
):
    """Record actual revenue and cost after job completion."""
    repo = JobRepository(db)
    job = await repo.get(job_id, current_user.fleet_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return await repo.update(job, {
        "actual_revenue": payload.actual_revenue,
        "actual_cost": payload.actual_cost,
        "status": "completed",
    })
